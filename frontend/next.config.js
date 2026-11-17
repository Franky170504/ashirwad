/** @type {import('next').NextConfig} */
const DJANGO = process.env.DJANGO_API_URL || "http://127.0.0.1:8000";

module.exports = {
  reactStrictMode: true,
  // Proxy /* to Django so the browser sees a single origin.
  // This avoids CORS and lets Django's session / CSRF cookies work.
async rewrites() {
  return [{ source: "/api/:path*", destination: `${DJANGO}/:path*` }];
},
  // Django expects trailing slashes on its URLs
  skipTrailingSlashRedirect: true,
};
