/** @type {import('next').NextConfig} */
const nextConfig = {
    eslint: {
        ignoreDuringBuilds: true,   // ← disables eslint on vercel build
    },
    typescript: {
        ignoreBuildErrors: true,    // ← ignores type errors on vercel build
    },
    async rewrites() {
        return [
            {
                source: "/api/:path*",
                destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
            },
        ]
    },
}

module.exports = nextConfig