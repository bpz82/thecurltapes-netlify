// Cloudflare Pages Function: POST /api/contact
import { handleContact } from '../../lib/forms.js';
export const onRequestPost = ({ request, env }) => handleContact(request, env);
