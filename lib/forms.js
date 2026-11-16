// Shared form backend for thecurltapes.com (used by Cloudflare Pages Functions and Netlify Functions).
// Everything is configured with environment variables — see README "Forms & newsletter".
//
//   RESEND_API_KEY        send notification emails via resend.com (contact, orders, and signup copies)
//   MAIL_FROM             verified sender, e.g. "The Curl Tapes <site@thecurltapes.com>"
//   MAIL_TO               where messages go (default thecurltapes@gmail.com)
//   MAIL_TO_COLEMAN       optional, for the "Message Coleman" form (defaults to MAIL_TO)
//   MAIL_TO_BLAKE         optional, for the "Message Blake" form (defaults to MAIL_TO)
//   BUTTONDOWN_API_KEY    newsletter list on buttondown.com            } use one of these for the
//   MAILCHIMP_API_KEY + MAILCHIMP_LIST_ID   newsletter list on Mailchimp } email list itself
//
// If nothing is configured the endpoints answer 503 and the site shows the visitor a
// pre-filled email link instead, so nothing is ever silently dropped.

const json = (status, obj) =>
  new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });
const isEmail = (s) => typeof s === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) && s.length < 255;
const clean = (s, n = 5000) => String(s == null ? '' : s).slice(0, n).trim();

async function readBody(request) {
  const type = request.headers.get('content-type') || '';
  if (type.includes('application/json')) return await request.json();
  const f = await request.formData();
  return Object.fromEntries(f.entries());
}

async function sendMail(env, { to, subject, text, replyTo }) {
  if (!env.RESEND_API_KEY || !env.MAIL_FROM) return false;
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: env.MAIL_FROM, to: [to], subject, text, reply_to: replyTo || undefined }),
  });
  if (!r.ok) throw new Error('Email provider error ' + r.status + ' ' + (await r.text()).slice(0, 200));
  return true;
}

async function addToList(env, { email, fname, lname }) {
  if (env.BUTTONDOWN_API_KEY) {
    const r = await fetch('https://api.buttondown.com/v1/subscribers', {
      method: 'POST',
      headers: { Authorization: `Token ${env.BUTTONDOWN_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_address: email, metadata: { first_name: fname, last_name: lname }, tags: ['website'] }),
    });
    if (r.ok || r.status === 409) return 'buttondown';
    const t = await r.text();
    if (/already/i.test(t)) return 'buttondown';
    throw new Error('Buttondown error ' + r.status + ' ' + t.slice(0, 200));
  }
  if (env.MAILCHIMP_API_KEY && env.MAILCHIMP_LIST_ID) {
    const dc = env.MAILCHIMP_API_KEY.split('-').pop();
    const r = await fetch(`https://${dc}.api.mailchimp.com/3.0/lists/${env.MAILCHIMP_LIST_ID}/members`, {
      method: 'POST',
      headers: { Authorization: 'Basic ' + btoa('any:' + env.MAILCHIMP_API_KEY), 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_address: email, status: env.MAILCHIMP_STATUS || 'subscribed', merge_fields: { FNAME: fname, LNAME: lname } }),
    });
    if (r.ok) return 'mailchimp';
    const t = await r.text();
    if (/Member Exists/i.test(t)) return 'mailchimp';
    throw new Error('Mailchimp error ' + r.status + ' ' + t.slice(0, 200));
  }
  return null;
}

export async function handleSubscribe(request, env) {
  let d;
  try { d = await readBody(request); } catch { return json(400, { ok: false, error: 'Bad request' }); }
  if (d.website) return json(200, { ok: true }); // honeypot
  const email = clean(d.email, 254), fname = clean(d.fname, 100), lname = clean(d.lname, 100);
  if (!isEmail(email)) return json(400, { ok: false, error: 'Please enter a valid email address.' });
  try {
    const list = await addToList(env, { email, fname, lname });
    const mailed = await sendMail(env, {
      to: env.MAIL_TO || 'thecurltapes@gmail.com',
      subject: `New email-list signup: ${fname} ${lname}`.trim(),
      text: `Name: ${fname} ${lname}\nEmail: ${email}\nPage: ${clean(d.page, 200)}\nSaved to list: ${list || 'no list configured (add them by hand)'}`,
      replyTo: email,
    });
    if (!list && !mailed) return json(503, { ok: false, error: 'Signup storage is not configured.' });
    return json(200, { ok: true });
  } catch (e) {
    return json(502, { ok: false, error: String(e.message || e) });
  }
}

export async function handleContact(request, env) {
  let d;
  try { d = await readBody(request); } catch { return json(400, { ok: false, error: 'Bad request' }); }
  if (d.website) return json(200, { ok: true });
  const email = clean(d.email, 254);
  if (!isEmail(email) || !clean(d.message)) return json(400, { ok: false, error: 'Email and message are required.' });
  const r = clean(d.recipient, 40);
  const to = (r === 'coleman' && env.MAIL_TO_COLEMAN) || (r === 'blake' && env.MAIL_TO_BLAKE) || env.MAIL_TO || 'thecurltapes@gmail.com';
  const who = { coleman: 'Coleman', blake: 'Blake', 'coleman-and-blake': 'Coleman & Blake', 'store-questions': 'Store question' }[r] || 'Website';
  const text = [
    `Form: ${clean(d.form, 120)} (${who})`,
    `Name: ${clean(d.fname, 100)} ${clean(d.lname, 100)}`,
    `Email: ${email}`,
    d.phone ? `Phone: ${clean(d.phone, 40)}` : null,
    d.newsletter_optin ? `Sign up for news and updates: ${clean(d.newsletter_optin, 5)}` : null,
    `Page: ${clean(d.page, 200)}`,
    '',
    clean(d.message),
  ].filter((x) => x !== null).join('\n');
  try {
    const mailed = await sendMail(env, { to, subject: `[thecurltapes.com] Message for ${who} from ${clean(d.fname, 100)}`, text, replyTo: email });
    if (!mailed) return json(503, { ok: false, error: 'Email delivery is not configured.' });
    if (d.newsletter_optin === 'yes') {
      try { await addToList(env, { email, fname: clean(d.fname, 100), lname: clean(d.lname, 100) }); } catch {}
    }
    return json(200, { ok: true });
  } catch (e) {
    return json(502, { ok: false, error: String(e.message || e) });
  }
}

export async function handleOrder(request, env) {
  let d;
  try { d = await readBody(request); } catch { return json(400, { ok: false, error: 'Bad request' }); }
  const items = Array.isArray(d.items) ? d.items.slice(0, 20) : [];
  if (!items.length) return json(400, { ok: false, error: 'Cart is empty.' });
  const emails = [];
  const lines = items.map((it) => {
    const info = it.info && typeof it.info === 'object' ? it.info : {};
    Object.values(info).forEach((v) => { if (isEmail(String(v))) emails.push(String(v)); });
    const qty = Math.max(1, Math.min(99, parseInt(it.qty, 10) || 1));
    return `${qty} × ${clean(it.title, 200)} @ $${((+it.price || 0) / 100).toFixed(2)}\n` +
      Object.entries(info).map(([k, v]) => `   ${clean(k, 80)}: ${clean(v, 1000)}`).join('\n');
  });
  const text = `New ticket/order REQUEST from the website (no payment has been taken).\n\n${lines.join('\n\n')}\n\nTotal shown to buyer: ${clean(d.total, 20)}\n\nReply to the buyer to confirm and arrange payment.`;
  try {
    const mailed = await sendMail(env, { to: env.MAIL_TO || 'thecurltapes@gmail.com', subject: '[thecurltapes.com] New order request', text, replyTo: emails[0] });
    if (!mailed) return json(503, { ok: false, error: 'Order requests are not configured.' });
    return json(200, { ok: true });
  } catch (e) {
    return json(502, { ok: false, error: String(e.message || e) });
  }
}

// blakezuniga.com in-page contact form (POST /api/bz-contact).
// Called from blakezuniga.com / www / the surge preview; CORS is origin-restricted.
const BZ_ALLOWED_ORIGINS = [
  'https://blakezuniga.com',
  'https://www.blakezuniga.com',
  'https://bpz-guitar-versions.surge.sh',
];
const BZ_NAME_MAX = 200;
const BZ_EMAIL_MAX = 254;
const BZ_PHONE_MAX = 40;
const BZ_MESSAGE_MAX = 5000;

function bzCorsHeaders(origin) {
  if (!BZ_ALLOWED_ORIGINS.includes(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Vary': 'Origin',
  };
}

function bzJson(status, obj, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...bzCorsHeaders(origin) },
  });
}

export async function handleBzContact(request, env) {
  const origin = request.headers.get('Origin') || '';
  if (request.method === 'OPTIONS') {
    if (!BZ_ALLOWED_ORIGINS.includes(origin)) return new Response(null, { status: 403 });
    return new Response(null, { status: 204, headers: bzCorsHeaders(origin) });
  }
  if (request.method && request.method !== 'POST') {
    return bzJson(405, { ok: false, error: 'Method not allowed' }, origin);
  }
  if (origin && !BZ_ALLOWED_ORIGINS.includes(origin)) {
    return new Response(JSON.stringify({ ok: false, error: 'Forbidden' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  let d;
  try { d = await readBody(request); } catch { return bzJson(400, { ok: false, error: 'Bad request' }, origin); }
  if (d.website) return bzJson(200, { ok: true }, origin); // honeypot: silent fake success
  const name = clean(d.name, BZ_NAME_MAX).replace(/[\r\n]+/g, ' ');
  const email = clean(d.email, BZ_EMAIL_MAX);
  const phone = clean(d.phone, BZ_PHONE_MAX);
  const message = clean(d.message, BZ_MESSAGE_MAX);
  if (!name || !isEmail(email) || !message) {
    return bzJson(400, { ok: false, error: 'Name, a valid email, and a message are required.' }, origin);
  }
  const text = [
    `Name: ${name}`,
    `Email: ${email}`,
    phone ? `Phone: ${phone}` : null,
    '',
    message,
  ].filter((x) => x !== null).join('\n');
  try {
    const mailed = await sendMail(env, {
      to: env.MAIL_TO_BLAKEZUNIGA || 'bpz82bear@gmail.com',
      subject: `[blakezuniga.com] Message from ${name}`,
      text,
      replyTo: email,
    });
    if (!mailed) return bzJson(503, { ok: false, error: 'Email delivery is not configured.' }, origin);
    return bzJson(200, { ok: true }, origin);
  } catch (e) {
    return bzJson(502, { ok: false, error: String(e.message || e) }, origin);
  }
}
