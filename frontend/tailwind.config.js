/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx}",
        "./components/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    50: "#EFF6FF",
                    100: "#DBEAFE",
                    500: "#3B82F6",
                    600: "#2563EB",
                    700: "#1D4ED8",
                    900: "#1E3A5F",
                }
            },
            animation: {
                "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "fade-in": "fadeIn 0.4s ease-in-out",
            },
            keyframes: {
                fadeIn: {
                    "0%": { opacity: 0, transform: "translateY(8px)" },
                    "100%": { opacity: 1, transform: "translateY(0)" },
                }
            }
        },
    },
    plugins: [],
}