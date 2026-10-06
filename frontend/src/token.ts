const TOKEN_KEY = "aisaac.dashboardToken";

export function readToken(): string {
  try {
    return window.localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function writeToken(value: string): void {
  try {
    if (value) window.localStorage.setItem(TOKEN_KEY, value);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage can be blocked; the token then lasts for this page view only.
  }
}

// The write token authorizes state changes (resolving incidents). It lives in sessionStorage so it
// is dropped when the tab closes and is never shared with the persisted read token.
const WRITE_TOKEN_KEY = "aisaac.dashboardWriteToken";

export function readWriteToken(): string {
  try {
    return window.sessionStorage.getItem(WRITE_TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function writeWriteToken(value: string): void {
  try {
    if (value) window.sessionStorage.setItem(WRITE_TOKEN_KEY, value);
    else window.sessionStorage.removeItem(WRITE_TOKEN_KEY);
  } catch {
    // Storage can be blocked; resolving then requires re-entering the token.
  }
}
