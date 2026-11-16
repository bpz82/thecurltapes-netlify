// Smoke test for Curl Tapes form handlers.
// No env vars: contact/subscribe/order should return 503 for valid payloads.
// Honeypot (website field): contact and subscribe should return a fake 200 success.
// Never loosen these expectations.
// Run from the repository root: node tests/smoke-forms.mjs

import { handleContact, handleOrder, handleSubscribe, handleBzContact } from '../lib/forms.js';
import contactFn from '../netlify/functions/contact.mjs';
import orderFn from '../netlify/functions/order.mjs';
import subscribeFn from '../netlify/functions/subscribe.mjs';
import bzContactFn from '../netlify/functions/bz-contact.mjs';

const emptyEnv = {};
let failed = 0;
let passed = 0;

async function post(body) {
  return new Request('https://example.com/api', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function call(handler, body, env) {
  const res = await handler(await post(body), env);
  let json;
  try { json = await res.json(); } catch { json = null; }
  return { status: res.status, json };
}

async function expect(name, got, wantStatus, wantOk) {
  const ok = got.status === wantStatus && got.json && got.json.ok === wantOk;
  if (ok) {
    passed += 1;
    console.log(`PASS  ${name}  status=${got.status}  body=${JSON.stringify(got.json)}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${name}  got status=${got.status} body=${JSON.stringify(got.json)}  want status=${wantStatus} ok=${wantOk}`);
  }
}

const contactBody = {
  email: 'visitor@example.com',
  message: 'Hello from the smoke test',
  fname: 'Test',
  lname: 'Visitor',
  form: 'contact-6',
  recipient: 'coleman-and-blake',
  page: '/contact-6',
};
const subscribeBody = {
  email: 'visitor@example.com',
  fname: 'Test',
  lname: 'Visitor',
  page: '/',
};
const orderBody = {
  items: [{ title: 'Sparrow Nest Theater ticket', qty: 1, price: 2500, info: { Email: 'buyer@example.com' } }],
  total: '$25.00',
};

console.log('--- no env vars: expect 503 ---');
await expect('handleContact no env', await call(handleContact, contactBody, emptyEnv), 503, false);
await expect('handleSubscribe no env', await call(handleSubscribe, subscribeBody, emptyEnv), 503, false);
await expect('handleOrder no env', await call(handleOrder, orderBody, emptyEnv), 503, false);

console.log('--- honeypot (website field): expect fake success 200 ok:true ---');
await expect('handleContact honeypot', await call(handleContact, { ...contactBody, website: 'http://spam.example' }, emptyEnv), 200, true);
await expect('handleSubscribe honeypot', await call(handleSubscribe, { ...subscribeBody, website: 'http://spam.example' }, emptyEnv), 200, true);
// handleOrder does not implement a honeypot; document actual behavior, do not change it.
const orderHoney = await call(handleOrder, { ...orderBody, website: 'http://spam.example' }, emptyEnv);
console.log(`INFO  handleOrder honeypot (no honeypot in this handler)  status=${orderHoney.status} body=${JSON.stringify(orderHoney.json)}`);

console.log('--- Netlify function wrappers use process.env (unset): expect 503 ---');
async function callWrap(fn, body) {
  const res = await fn(await post(body));
  let json;
  try { json = await res.json(); } catch { json = null; }
  return { status: res.status, json };
}
await expect('contact.mjs no env', await callWrap(contactFn, contactBody), 503, false);
await expect('subscribe.mjs no env', await callWrap(subscribeFn, subscribeBody), 503, false);
await expect('order.mjs no env', await callWrap(orderFn, orderBody), 503, false);
await expect('contact.mjs honeypot', await callWrap(contactFn, { ...contactBody, website: 'http://spam.example' }), 200, true);
await expect('subscribe.mjs honeypot', await callWrap(subscribeFn, { ...subscribeBody, website: 'http://spam.example' }), 200, true);


const bzBody = {
  name: 'Website Test',
  email: 'visitor@example.com',
  phone: '555-0100',
  message: 'Hello from the smoke test',
};

console.log('--- handleBzContact no env vars: expect 503 ---');
await expect('handleBzContact no env', await call(handleBzContact, bzBody, emptyEnv), 503, false);
await expect('bz-contact.mjs no env', await callWrap(bzContactFn, bzBody), 503, false);

console.log('--- handleBzContact honeypot: expect fake success 200 ok:true ---');
await expect('handleBzContact honeypot', await call(handleBzContact, { ...bzBody, website: 'http://spam.example' }, emptyEnv), 200, true);
await expect('bz-contact.mjs honeypot', await callWrap(bzContactFn, { ...bzBody, website: 'http://spam.example' }), 200, true);

console.log('--- handleBzContact validation: expect 400 ---');
await expect('handleBzContact missing name', await call(handleBzContact, { ...bzBody, name: '' }, emptyEnv), 400, false);
await expect('handleBzContact missing email', await call(handleBzContact, { ...bzBody, email: '' }, emptyEnv), 400, false);
await expect('handleBzContact invalid email', await call(handleBzContact, { ...bzBody, email: 'not-an-email' }, emptyEnv), 400, false);
await expect('handleBzContact missing message', await call(handleBzContact, { ...bzBody, message: '' }, emptyEnv), 400, false);

async function bzRequest(handler, { method, body, origin, env, wrap }) {
  const headers = { 'Content-Type': 'application/json' };
  if (origin) headers.Origin = origin;
  const init = { method, headers };
  if (method === 'POST') init.body = JSON.stringify(body || {});
  const req = new Request('https://example.com/api/bz-contact', init);
  const res = wrap ? await handler(req) : await handler(req, env ?? emptyEnv);
  let json;
  try { json = await res.json(); } catch { json = null; }
  return { status: res.status, json, headers: res.headers };
}

function corsOk(got, origin) {
  const allow = got.headers.get('Access-Control-Allow-Origin');
  if (allow === origin) return true;
  return `CORS allow origin got=${allow} want=${origin}`;
}

async function expectCheck(name, ok, detail) {
  if (ok) {
    passed += 1;
    console.log(`PASS  ${name}  ${detail}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${name}  ${detail}`);
  }
}

const allowedOrigin = 'https://blakezuniga.com';
const surgeOrigin = 'https://bpz-guitar-versions.surge.sh';
const badOrigin = 'https://evil.example';

console.log('--- handleBzContact CORS ---');
{
  const opt = await bzRequest(handleBzContact, { method: 'OPTIONS', origin: allowedOrigin });
  await expectCheck('handleBzContact OPTIONS allowed origin', opt.status === 204 && corsOk(opt, allowedOrigin) === true,
    `status=${opt.status} allow=${opt.headers.get('Access-Control-Allow-Origin')}`);
  const optWww = await bzRequest(handleBzContact, { method: 'OPTIONS', origin: 'https://www.blakezuniga.com' });
  await expectCheck('handleBzContact OPTIONS www origin', optWww.status === 204 && corsOk(optWww, 'https://www.blakezuniga.com') === true,
    `status=${optWww.status} allow=${optWww.headers.get('Access-Control-Allow-Origin')}`);
  const optSurge = await bzRequest(handleBzContact, { method: 'OPTIONS', origin: surgeOrigin });
  await expectCheck('handleBzContact OPTIONS surge origin', optSurge.status === 204 && corsOk(optSurge, surgeOrigin) === true,
    `status=${optSurge.status} allow=${optSurge.headers.get('Access-Control-Allow-Origin')}`);
  const optBad = await bzRequest(handleBzContact, { method: 'OPTIONS', origin: badOrigin });
  await expectCheck('handleBzContact OPTIONS disallowed origin', optBad.status === 403 && !optBad.headers.get('Access-Control-Allow-Origin'),
    `status=${optBad.status} allow=${optBad.headers.get('Access-Control-Allow-Origin')}`);
  const postBad = await bzRequest(handleBzContact, { method: 'POST', body: bzBody, origin: badOrigin });
  await expectCheck('handleBzContact POST disallowed origin', postBad.status === 403 && postBad.json && postBad.json.ok === false && !postBad.headers.get('Access-Control-Allow-Origin'),
    `status=${postBad.status} body=${JSON.stringify(postBad.json)} allow=${postBad.headers.get('Access-Control-Allow-Origin')}`);
  const postOk = await bzRequest(handleBzContact, { method: 'POST', body: bzBody, origin: allowedOrigin });
  await expectCheck('handleBzContact POST allowed origin no env has CORS and 503',
    postOk.status === 503 && postOk.json && postOk.json.ok === false && corsOk(postOk, allowedOrigin) === true,
    `status=${postOk.status} body=${JSON.stringify(postOk.json)} allow=${postOk.headers.get('Access-Control-Allow-Origin')}`);
  const wrapOpt = await bzRequest(bzContactFn, { method: 'OPTIONS', origin: allowedOrigin, wrap: true });
  await expectCheck('bz-contact.mjs OPTIONS allowed origin', wrapOpt.status === 204 && corsOk(wrapOpt, allowedOrigin) === true,
    `status=${wrapOpt.status} allow=${wrapOpt.headers.get('Access-Control-Allow-Origin')}`);
}

console.log(`--- ${passed} passed, ${failed} failed ---`);
process.exit(failed ? 1 : 0);
