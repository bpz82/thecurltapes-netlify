// Smoke test for Curl Tapes form handlers.
// No env vars: contact/subscribe/order should return 503 for valid payloads.
// Honeypot (website field): contact and subscribe should return a fake 200 success.
// Never loosen these expectations.
// Run from the repository root: node tests/smoke-forms.mjs

import { handleContact, handleOrder, handleSubscribe } from '../lib/forms.js';
import contactFn from '../netlify/functions/contact.mjs';
import orderFn from '../netlify/functions/order.mjs';
import subscribeFn from '../netlify/functions/subscribe.mjs';

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

console.log(`--- ${passed} passed, ${failed} failed ---`);
process.exit(failed ? 1 : 0);
