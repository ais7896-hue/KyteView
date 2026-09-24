/**
 * Kyte 系列軟體雲端授權驗證與管理系統 (Cloudflare Workers + KV)
 * 支援產品：
 *  - KyteShelf 專用序號 (KS-XXXX-XXXX-XXXX)
 *  - KyteView 專用序號 (KV-XXXX-XXXX-XXXX)
 *  - 全家桶 / 雙工具組合包 (KB-XXXX-XXXX-XXXX，Kyte Bundle)
 *  - 同時向下相容舊版 KyteShelf 序號 (KYTE-XXXX-XXXX-XXXX)
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Admin-Secret, User-Agent",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // 1. 客戶端：線上啟用序號
      if (path === "/api/activate" && request.method === "POST") {
        return await handleActivate(request, env, corsHeaders);
      }

      // 2. 客戶端：解除設備綁定
      if (path === "/api/deactivate" && request.method === "POST") {
        return await handleDeactivate(request, env, corsHeaders);
      }

      // 3. 管理端：批次產生序號 (需 X-Admin-Secret)
      if (path === "/api/admin/generate-keys" && request.method === "POST") {
        return await handleAdminGenerate(request, env, corsHeaders);
      }

      // 4. 管理端：查詢序號使用狀況
      if (path === "/api/admin/query-key" && request.method === "GET") {
        return await handleAdminQuery(request, env, corsHeaders);
      }

      // 首頁 / 健康檢查
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "Kyte Multi-Product License Hub",
          version: "2.1.0",
          supported_prefixes: {
            "KS": "KyteShelf 專用",
            "KV": "KyteView 專用",
            "KB": "Kyte 全家桶 / 組合包",
            "KYTE": "舊版相容"
          }
        }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    } catch (err) {
      return new Response(
        JSON.stringify({ success: false, message: "伺服器內部錯誤：" + err.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
  },
};

/**
 * 客戶端啟用序號
 */
async function handleActivate(request, env, corsHeaders) {
  const body = await request.json();
  const rawKey = body.key ? body.key.trim().toUpperCase() : "";
  const machineId = body.machine_id ? body.machine_id.trim() : "";
  const machineName = body.machine_name || "Windows Device";
  const reqProduct = (body.product || (rawKey.startsWith("KV") ? "kyteview" : "kyteshelf")).toLowerCase();

  if (!rawKey || !machineId) {
    return jsonResponse(
      { success: false, message: "請提供序號 (key) 與硬體識別碼 (machine_id)" },
      400,
      corsHeaders
    );
  }

  const kvKey = `license:${rawKey}`;
  const recordStr = await env.KYTE_LICENSES.get(kvKey);

  if (!recordStr) {
    return jsonResponse(
      { success: false, message: "查無此授權序號，請確認輸入是否正確。" },
      404,
      corsHeaders
    );
  }

  const record = JSON.parse(recordStr);

  if (record.status !== "active") {
    return jsonResponse(
      { success: false, message: "此序號已被停用或作廢，請聯繫官方客服。" },
      403,
      corsHeaders
    );
  }

  // 判定產品歸屬 (支援 kyteshelf, kyteview, all, bundle)
  let licProduct = record.product;
  if (!licProduct) {
    if (rawKey.startsWith("KV") || rawKey.startsWith("KYTEVIEW")) licProduct = "kyteview";
    else if (rawKey.startsWith("KB") || rawKey.startsWith("KYTEALL")) licProduct = "all";
    else licProduct = "kyteshelf";
  }
  licProduct = licProduct.toLowerCase();

  const isMatch = (
    licProduct === "all" ||
    licProduct === "bundle" ||
    licProduct === reqProduct ||
    (Array.isArray(record.product) && record.product.includes(reqProduct))
  );

  if (!isMatch) {
    const prodName = licProduct === "kyteview" ? "KyteView" : "KyteShelf";
    return jsonResponse(
      { success: false, message: `此序號為 ${prodName} 專用序號，無法用於解鎖本軟體。` },
      403,
      corsHeaders
    );
  }

  const maxDevices = record.max_devices || 2;
  
  // 相容 activated_devices (字串陣列) 與 machines (物件陣列) 雙結構
  let activatedDevices = record.activated_devices || [];
  let machines = record.machines || [];

  // 若原有資料只存在 machines，同步提取至 activatedDevices
  if (activatedDevices.length === 0 && machines.length > 0) {
    activatedDevices = machines.map(m => typeof m === "string" ? m : m.machine_id);
  }

  const alreadyActive = activatedDevices.some(id => id.toLowerCase() === machineId.toLowerCase());

  if (!alreadyActive) {
    if (activatedDevices.length >= maxDevices) {
      return jsonResponse(
        {
          success: false,
          code: "DEVICE_LIMIT_EXCEEDED",
          message: `此序號已在 ${activatedDevices.length} 台電腦啟用（上限 ${maxDevices} 台）。若欲更換電腦，請在舊電腦上點選「解除綁定」。`,
        },
        403,
        corsHeaders
      );
    }

    activatedDevices.push(machineId);
    machines.push({
      machine_id: machineId,
      machine_name: machineName,
      activated_at: new Date().toISOString(),
    });

    record.activated_devices = activatedDevices;
    record.machines = machines;
    await env.KYTE_LICENSES.put(kvKey, JSON.stringify(record));
  }

  // 簽發授權 Token (使用 JWT_SECRET 簽名)
  const secretKey = env.JWT_SECRET || "KyteShelf_Secret_2026_@KeySecure";
  const token = await generateSignedToken(
    {
      key: rawKey,
      machine_id: machineId,
      product: licProduct,
      issued_at: Date.now(),
      type: "lifetime",
    },
    secretKey
  );

  return jsonResponse(
    {
      success: true,
      message: "啟用成功！已綁定至此電腦",
      token: token,
      devices_used: activatedDevices.length,
      max_devices: maxDevices,
      product: licProduct
    },
    200,
    corsHeaders
  );
}

/**
 * 客戶端解除綁定
 */
async function handleDeactivate(request, env, corsHeaders) {
  const body = await request.json();
  const rawKey = body.key ? body.key.trim().toUpperCase() : "";
  const machineId = body.machine_id ? body.machine_id.trim() : "";

  if (!rawKey || !machineId) {
    return jsonResponse({ success: false, message: "請提供序號與機器識別碼" }, 400, corsHeaders);
  }

  const kvKey = `license:${rawKey}`;
  const recordStr = await env.KYTE_LICENSES.get(kvKey);

  if (!recordStr) {
    return jsonResponse({ success: false, message: "查無此序號" }, 404, corsHeaders);
  }

  const record = JSON.parse(recordStr);
  let activatedDevices = record.activated_devices || [];
  let machines = record.machines || [];

  record.activated_devices = activatedDevices.filter(id => id.toLowerCase() !== machineId.toLowerCase());
  record.machines = machines.filter(m => (typeof m === "string" ? m : m.machine_id).toLowerCase() !== machineId.toLowerCase());

  await env.KYTE_LICENSES.put(kvKey, JSON.stringify(record));

  return jsonResponse(
    {
      success: true,
      message: "已成功解除此電腦綁定，名額已釋放",
      devices_used: record.activated_devices.length,
      max_devices: record.max_devices || 2,
    },
    200,
    corsHeaders
  );
}

/**
 * 管理端：批次產生序號
 * 支援 product: "kyteshelf" | "kyteview" | "all"
 * 前綴規範：
 *  - KS-XXXX-XXXX-XXXX (KyteShelf)
 *  - KV-XXXX-XXXX-XXXX (KyteView)
 *  - KB-XXXX-XXXX-XXXX (全家桶組合包)
 */
async function handleAdminGenerate(request, env, corsHeaders) {
  const adminSecret = request.headers.get("X-Admin-Secret");
  const expectedSecret = env.ADMIN_SECRET || "AdminSuperSecret_2026";

  if (!adminSecret || adminSecret !== expectedSecret) {
    return jsonResponse({ success: false, message: "管理員身分驗證失敗" }, 401, corsHeaders);
  }

  const body = await request.json().catch(() => ({}));
  const count = Math.min(Math.max(body.count || 10, 1), 100);
  const maxDevices = body.max_devices || 2;
  const product = (body.product || "kyteview").toLowerCase();
  const email = body.email || "";
  const note = body.note || `${product} Shopee Batch`;

  let prefix = "KV";
  if (product === "kyteshelf") {
    prefix = "KS";
  } else if (product === "all" || product === "bundle") {
    prefix = "KB";
  }

  if (body.prefix) {
    prefix = body.prefix.trim().toUpperCase();
  }

  const dateStr = new Date().toISOString().split("T")[0];
  const generatedKeys = [];

  for (let i = 0; i < count; i++) {
    const key = generateLicenseKey(prefix);
    const record = {
      product: product,
      email: email,
      created_at: dateStr,
      activated_devices: [],
      machines: [],
      max_devices: maxDevices,
      status: "active",
      note: note,
    };

    await env.KYTE_LICENSES.put(`license:${key}`, JSON.stringify(record));
    generatedKeys.push(key);
  }

  return jsonResponse(
    {
      success: true,
      product: product,
      prefix: prefix,
      count: generatedKeys.length,
      max_devices: maxDevices,
      keys: generatedKeys,
    },
    200,
    corsHeaders
  );
}

/**
 * 管理端：查詢序號使用狀況
 */
async function handleAdminQuery(request, env, corsHeaders) {
  const adminSecret = request.headers.get("X-Admin-Secret");
  const expectedSecret = env.ADMIN_SECRET || "AdminSuperSecret_2026";

  if (!adminSecret || adminSecret !== expectedSecret) {
    return jsonResponse({ success: false, message: "管理員身分驗證失敗" }, 401, corsHeaders);
  }

  const url = new URL(request.url);
  const key = (url.searchParams.get("key") || "").trim().toUpperCase();

  if (!key) {
    return jsonResponse({ success: false, message: "請帶入 key 參數" }, 400, corsHeaders);
  }

  const recordStr = await env.KYTE_LICENSES.get(`license:${key}`);
  if (!recordStr) {
    return jsonResponse({ success: false, message: "查無此序號" }, 404, corsHeaders);
  }

  return jsonResponse({ success: true, data: JSON.parse(recordStr) }, 200, corsHeaders);
}

// 輔助函式：產生隨機序號 (PREFIX-XXXX-XXXX-XXXX，排除易混淆字元)
function generateLicenseKey(prefix = "KV") {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // 排除易混淆 O, 0, I, 1
  let result = prefix;
  for (let block = 0; block < 3; block++) {
    let segment = "";
    for (let i = 0; i < 4; i++) {
      segment += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    result += "-" + segment;
  }
  return result;
}

// 輔助函式：簽發 HMAC-SHA256 Token
async function generateSignedToken(payload, secret) {
  const enc = new TextEncoder();
  const payloadStr = JSON.stringify(payload);
  const payloadB64 = btoa(unescape(encodeURIComponent(payloadStr)));

  const keyData = enc.encode(secret);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyData,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signatureBuffer = await crypto.subtle.sign("HMAC", cryptoKey, enc.encode(payloadB64));
  const signatureB64 = btoa(String.fromCharCode(...new Uint8Array(signatureBuffer)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

  return `${payloadB64}.${signatureB64}`;
}

function jsonResponse(data, status, headers) {
  return new Response(JSON.stringify(data, null, 2), {
    status: status,
    headers: {
      ...headers,
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
