// Netlify Function: POST /api/subscribe
import { handleSubscribe } from '../../lib/forms.js';
export default (request) => handleSubscribe(request, process.env);
export const config = { path: '/api/subscribe' };
