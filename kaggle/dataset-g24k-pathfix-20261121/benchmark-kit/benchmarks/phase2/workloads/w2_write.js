import http from 'k6/http';
import { check } from 'k6';
import exec from 'k6/execution';
import { Counter, Rate } from 'k6/metrics';

const fixture = JSON.parse(open(__ENV.ACTORS_FILE || '/runtime/actors.json'));
const baseUrl = __ENV.BASE_URL || 'http://backend:8080';
const smoke = (__ENV.BENCH_MODE || '') === 'smoke';
const vus = Math.min(Number(__ENV.WRITE_VUS || (smoke ? '2' : '10')), fixture.write.length);

const businessRejections = new Counter('business_rejections');
const serverErrors = new Counter('server_errors');
const unexpectedResponses = new Counter('unexpected_responses');
const writeErrorRate = new Rate('write_error_rate');

export const options = {
  scenarios: smoke
    ? { write_flow: { executor: 'shared-iterations', exec: 'writeFlow', vus, iterations: vus, maxDuration: '45s', tags: { workload: 'w2' } } }
    : { write_flow: { executor: 'constant-vus', exec: 'writeFlow', vus, duration: __ENV.MEASUREMENT_DURATION || '180s', gracefulStop: '30s', tags: { workload: 'w2' } } },
  summaryTrendStats: ['avg', 'min', 'med', 'p(50)', 'p(90)', 'p(95)', 'p(99)', 'max'],
  systemTags: ['status', 'method', 'url', 'name', 'scenario', 'group'],
};

function outcome(response, expected, operation) {
  const ok = response.status === expected;
  check(response, { [`${operation} status ${expected}`]: () => ok }, { workload: 'w2', operation });
  writeErrorRate.add(!ok, { workload: 'w2', operation });
  if (!ok) {
    unexpectedResponses.add(1, { workload: 'w2', operation, status: String(response.status) });
    if (response.status === 409 || response.status === 400) businessRejections.add(1, { operation, status: String(response.status) });
    if (response.status >= 500 || response.status === 0) serverErrors.add(1, { operation, status: String(response.status) });
  }
  return ok;
}

export function writeFlow() {
  const actor = fixture.write[(exec.vu.idInTest - 1) % fixture.write.length];
  const params = { headers: { Authorization: `Bearer ${actor.token}`, 'Content-Type': 'application/json' }, tags: { workload: 'w2' } };

  const added = http.post(`${baseUrl}/api/cart/items`, JSON.stringify({ foodId: actor.food_id, quantity: 1 }), { ...params, tags: { workload: 'w2', operation: 'cart_add' } });
  if (!outcome(added, 200, 'cart_add')) return;
  let cart;
  try { cart = added.json(); } catch (_) { unexpectedResponses.add(1, { operation: 'cart_add_json' }); return; }
  const cartItem = cart.items && cart.items.find((item) => item.food && item.food.id === actor.food_id);
  if (!cartItem) { unexpectedResponses.add(1, { operation: 'cart_item_missing' }); return; }

  const updated = http.put(`${baseUrl}/api/cart/items/${cartItem.id}`, JSON.stringify({ quantity: 2 }), { ...params, tags: { workload: 'w2', operation: 'cart_update' } });
  if (!outcome(updated, 200, 'cart_update')) return;

  const checkout = http.post(`${baseUrl}/api/orders`, JSON.stringify({
    orderType: 'DINE_IN', tableNumber: `B${actor.id}`, recipientName: null,
    shippingPhone: null, shippingAddress: null, paymentMethod: 'CASH', note: 'benchmark-w2',
  }), { ...params, tags: { workload: 'w2', operation: 'checkout' } });
  if (!outcome(checkout, 201, 'checkout')) return;
  let order;
  try { order = checkout.json(); } catch (_) { unexpectedResponses.add(1, { operation: 'checkout_json' }); return; }

  const cancelled = http.del(`${baseUrl}/api/orders/${order.id}`, null, { ...params, tags: { workload: 'w2', operation: 'cancel' } });
  outcome(cancelled, 200, 'cancel');
}

export function handleSummary(data) {
  const path = __ENV.SUMMARY_PATH || '/results/w2-summary.json';
  const compact = {
    workload: 'W2', mode: smoke ? 'smoke' : 'measurement', vus,
    checks: data.metrics.checks && data.metrics.checks.values,
    httpReqDuration: data.metrics.http_req_duration && data.metrics.http_req_duration.values,
    httpReqFailed: data.metrics.http_req_failed && data.metrics.http_req_failed.values,
    httpReqs: data.metrics.http_reqs && data.metrics.http_reqs.values,
    businessRejections: data.metrics.business_rejections && data.metrics.business_rejections.values,
    serverErrors: data.metrics.server_errors && data.metrics.server_errors.values,
    writeErrorRate: data.metrics.write_error_rate && data.metrics.write_error_rate.values,
  };
  return { [path]: JSON.stringify(data, null, 2), stdout: `${JSON.stringify(compact)}\n` };
}
