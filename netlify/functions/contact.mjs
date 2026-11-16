// Netlify Function: POST /api/contact
import { handleContact, withSiteCors } from '../../lib/forms.js';
export default (request) => withSiteCors(handleContact)(request, process.env);
export const config = { path: '/api/contact' };
