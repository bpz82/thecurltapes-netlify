// Netlify Function: POST /api/contact
import { handleContact } from '../../lib/forms.js';
export default (request) => handleContact(request, process.env);
export const config = { path: '/api/contact' };
