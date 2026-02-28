import { Hero } from "./Hero";
import { BentoGrid } from "./BentoGrid";
import { Architecture } from "./Architecture";
import { CodeExample } from "./CodeExample";
import { Installation } from "./Installation";
import { CTA } from "./CTA";

export function LandingPage() {
    return (
        <>
            <Hero />
            <BentoGrid />
            <Architecture />
            <CodeExample />
            <Installation />
            <CTA />
        </>
    );
}
