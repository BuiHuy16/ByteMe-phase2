import http from 'k6/http';
import { check } from 'k6';
import { Counter, Rate } from 'k6/metrics';

const fixture = JSON.parse(open(__ENV.ACTORS_FILE || '/runtime/actors.json'));
const baseUrl = __ENV.BASE_URL || 'http://backend:8080';
const smoke = (__ENV.BENCH_MODE || '') === 'smoke';
const duration = __ENV.MEASUREMENT_DURATION || '180s';
const pageSize = Number(__ENV.ORDER_PAGE_SIZE || '20');

const unexpectedResponses = new Counter('unexpected_responses');
const applicationErrorRate = new Rate('application_error_rate');

function scenario(name, rate) {
  if (smoke) {
    return { executor: 'shared-iterations', exec: name, vus: 1, iterations: 2, maxDuration: '30s', tags: { workload: 'w1', operation: name } };
  }
  return {
    executor: 'constant-arrival-rate', exec: name, rate, timeUnit: '1s', duration,
    preAllocatedVUs: Math.max(2, rate), maxVUs: Math.max(10, rate * 4),
    tags: { workload: 'w1', operation: name },
  };
}

export const options = {
  scenarios: {
    food_list: scenario('foodList', Number(__ENV.FOOD_LIST_RPS || '10')),
    food_search: scenario('foodSearch', Number(__ENV.FOOD_SEARCH_RPS || '5')),
    order_list: scenario('orderList', Number(__ENV.ORDER_LIST_RPS || '5')),
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(50)', 'p(90)', 'p(95)', 'p(99)', 'max'],
  systemTags: ['status', 'method', 'url', 'name', 'scenario', 'group'],
};

function record(response, expectedStatus, label) {
  const ok = response.status === expectedStatus;
  check(response, { [`${label} status ${expectedStatus}`]: () => ok }, { workload: 'w1', operation: label });
  applicationErrorRate.add(!ok, { workload: 'w1', operation: label });
  if (!ok) unexpectedResponses.add(1, { workload: 'w1', operation: label, status: String(response.status) });
}

export function foodList() {
  const response = http.get(`${baseUrl}/api/foods`, { tags: { workload: 'w1', operation: 'food_list' } });
  record(response, 200, 'food_list');
}

export function foodSearch() {
  const response = http.get(`${baseUrl}/api/foods/search?q=needle`, { tags: { workload: 'w1', operation: 'food_search' } });
  record(response, 200, 'food_search');
}

export function orderList() {
  const response = http.get(`${baseUrl}/api/orders?page=0&size=${pageSize}`, {
    headers: { Authorization: `Bearer ${fixture.read.token}` },
    tags: { workload: 'w1', operation: 'order_list', page_size: String(pageSize) },
  });
  record(response, 200, 'order_list');
}

export function handleSummary(data) {
  const path = __ENV.SUMMARY_PATH || '/results/w1-summary.json';
  const compact = {
    workload: 'W1', mode: smoke ? 'smoke' : 'measurement', pageSize,
    checks: data.metrics.checks && data.metrics.checks.values,
    httpReqDuration: data.metrics.http_req_duration && data.metrics.http_req_duration.values,
    httpReqFailed: data.metrics.http_req_failed && data.metrics.http_req_failed.values,
    httpReqs: data.metrics.http_reqs && data.metrics.http_reqs.values,
    unexpectedResponses: data.metrics.unexpected_responses && data.metrics.unexpected_responses.values,
    applicationErrorRate: data.metrics.application_error_rate && data.metrics.application_error_rate.values,
  };
  return { [path]: JSON.stringify(data, null, 2), stdout: `${JSON.stringify(compact)}\n` };
}
