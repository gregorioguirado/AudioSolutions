import HeroDropZone from "@/components/HeroDropZone";
import HowItWorks from "@/components/HowItWorks";
import WhatTranslates from "@/components/WhatTranslates";
import PricingTeaser from "@/components/PricingTeaser";
import FAQ from "@/components/FAQ";

export default function Home() {
  return (
    <main>
      <HeroDropZone />
      <HowItWorks />
      <WhatTranslates />
      <PricingTeaser />
      <FAQ />
    </main>
  );
}
