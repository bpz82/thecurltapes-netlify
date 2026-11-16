// Cloudflare Pages Function: POST /api/order
import { handleOrder } from '../../lib/forms.js';
export const onRequestPost = ({ request, env }) => handleOrder(request, env);
