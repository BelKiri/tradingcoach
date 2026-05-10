import Link from "next/link";

const sections = [
  {
    title: "Products",
    links: [
      { label: "Trading History Analyzer", href: "/#how-it-works" },
      { label: "AI Coach", href: "/#pricing" },
      { label: "Trade Checker (coming soon)", href: "/#features" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Contact", href: "#" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Terms of Service", href: "#" },
      { label: "Privacy Policy", href: "#" },
      { label: "Risk Disclaimer", href: "#" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="border-t bg-card/50">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <span className="text-lg font-bold">TradeCoach</span>
            <p className="mt-2 text-sm text-muted-foreground">
              AI trading coach that fixes your habits, not your strategy.
            </p>
          </div>
          {sections.map((section) => (
            <div key={section.title}>
              <h4 className="mb-3 text-sm font-semibold">{section.title}</h4>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 border-t pt-6 text-center text-xs text-muted-foreground">
          <p>
            Trading involves risk. Past performance does not guarantee future
            results. TradeCoach provides analysis, not financial advice.
          </p>
          <p className="mt-2">&copy; 2026 TradeCoach. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
