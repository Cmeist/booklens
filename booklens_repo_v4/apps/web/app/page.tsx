const coreFields = [
  "Title",
  "Author",
  "Description",
  "Genre / subject tags",
  "Publication year",
  "Page count",
  "Rating count",
  "Average rating",
];

const mvpFeatures = [
  "Advanced book explorer",
  "Top 10 popular tags",
  "Book detail pages",
  "Similar-books recommendation prototype",
  "Recommendation explanation chips",
];

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">BookLens</p>
        <h1>Find better books faster.</h1>
        <p className="hero-copy">
          A portfolio-ready book discovery app focused on cleaner filtering, useful metadata,
          and explainable recommendations.
        </p>
        <div className="hero-actions">
          <a href="#features">View MVP scope</a>
          <a href="#data" className="secondary">Review data fields</a>
        </div>
      </section>

      <section id="features" className="card-grid" aria-labelledby="features-title">
        <div className="section-heading">
          <p className="eyebrow">MVP</p>
          <h2 id="features-title">Small, clean first build</h2>
        </div>
        {mvpFeatures.map((feature) => (
          <article className="card" key={feature}>
            <h3>{feature}</h3>
            <p>
              Build this only after the data pipeline produces a clean book catalog and tag counts.
            </p>
          </article>
        ))}
      </section>

      <section id="data" className="panel" aria-labelledby="data-title">
        <div>
          <p className="eyebrow">Dataset</p>
          <h2 id="data-title">Core fields</h2>
          <p>
            These fields power search, filters, top tags, book detail pages, and the first
            recommendation model.
          </p>
        </div>
        <ul className="field-list">
          {coreFields.map((field) => (
            <li key={field}>{field}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
