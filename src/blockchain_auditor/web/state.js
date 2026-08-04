export const state = {runs: [], run: null, jobs: [], events: [], architecture: null, assistance: null, simulation: null, monitoring: null, posture: null, compliance: null, copilot: null, reviews: {findings: {}, events: []}, role: "auditor", actor: "local-auditor", token: sessionStorage.getItem("auditToken") || ""};
export function setState(values) { Object.assign(state, values); }
