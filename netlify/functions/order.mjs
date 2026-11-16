// Netlify Function: POST /api/order
import { handleOrder } from '../../lib/forms.js';
export default (request) => handleOrder(request, process.env);
export const config = { path: '/api/order' };
