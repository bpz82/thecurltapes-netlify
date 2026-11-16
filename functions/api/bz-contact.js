// Cloudflare Pages Function: POST /api/bz-contact
import { handleBzContact } from '../../lib/forms.js';
export const onRequestPost = ({ request, env }) => handleBzContact(request, env);
export const onRequestOptions = ({ request, env }) => handleBzContact(request, env);
