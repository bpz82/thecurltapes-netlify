// Netlify Function: POST /api/subscribe
import { handleSubscribe, withSiteCors } from '../../lib/forms.js';
export default (request) => withSiteCors(handleSubscribe)(request, process.env);
export const config = { path: '/api/subscribe' };
