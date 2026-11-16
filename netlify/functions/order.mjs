// Netlify Function: POST /api/order
import { handleOrder, withSiteCors } from '../../lib/forms.js';
export default (request) => withSiteCors(handleOrder)(request, process.env);
export const config = { path: '/api/order' };
