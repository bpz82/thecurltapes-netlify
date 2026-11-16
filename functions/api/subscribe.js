// Cloudflare Pages Function: POST /api/subscribe
import { handleSubscribe } from '../../lib/forms.js';
export const onRequestPost = ({ request, env }) => handleSubscribe(request, env);
