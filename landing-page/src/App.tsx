import { Footer, Nav } from "./components/chrome";
import { Compare, Faq, Features, FinalCta, Hero, Privacy, Product } from "./sections";

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Product />
        <Features />
        <Privacy />
        <Compare />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
