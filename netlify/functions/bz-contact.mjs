// Netlify Function: POST /api/bz-contact
import { handleBzContact } from '../../lib/forms.js';
export default (request) => handleBzContact(request, process.env);
export const config = { path: '/api/bz-contact' };
