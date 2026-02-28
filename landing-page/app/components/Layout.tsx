import { Outlet } from "react-router";
import { Navigation } from "./Navigation";
import { Footer } from "./Footer";

export function Layout() {
    return (
        <div
            className="min-h-screen antialiased"
            style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}
        >
            <Navigation />
            <Outlet />
            <Footer />
        </div>
    );
}
