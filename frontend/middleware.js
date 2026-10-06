// Vercel Edge Middleware (project root: frontend/).
//
// Synaptiq has no verified, monitored security contact yet, so there is no
// security.txt. Without this, the single-page-app fallback would answer
// /.well-known/security.txt with the site's HTML and status 200, which
// scanners read as a malformed security.txt. Return a genuine 404 until a
// real contact exists; then publish a valid file and remove this rule.
export const config = { matcher: ["/.well-known/security.txt"] };

export default function middleware() {
  return new Response("Not found\n", {
    status: 404,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}
