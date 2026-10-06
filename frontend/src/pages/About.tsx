import { Link } from 'react-router-dom'

export default function About() {
  return (
    <>
      <section className="hero hero-small">
        <div className="container hero-inner">
          <p className="eyebrow">About Us</p>
          <h1>A New Haven shop with deep Yale roots</h1>
        </div>
      </section>

      <div className="container section prose">
        <p className="lead">
          Campus Customs has sold Yale gear on Broadway since 1973, just across from the Yale campus. The shop is
          still run by the family that started it, and we still love seeing a Bulldog logo on a new hoodie.
        </p>

        <div className="about-grid">
          <div>
            <h3>We make it ourselves</h3>
            <p>
              Most of our gear is screen printed or embroidered in our own local production shop. Doing the work
              ourselves lets us control quality, try new designs and keep favourites in stock in every size.
            </p>
          </div>
          <div>
            <h3>Gear for every corner of Yale</h3>
            <p>
              We carry classic block-letter designs and crests for every residential college, from Benjamin Franklin
              to Trumbull. We also stock designs for varsity teams, graduate and professional schools, and Yale
              families, including moms, dads and grandparents.
            </p>
          </div>
          <div>
            <h3>Officially licensed</h3>
            <p>
              The Bulldog designs on our shelves are officially licensed by Yale University, so the colours, marks
              and crests are the real thing.
            </p>
          </div>
          <div>
            <h3>Visit or reach out</h3>
            <p>
              Stop by <strong>57 Broadway, New Haven, CT 06511</strong>, or email{' '}
              <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a> with order questions.
              Unworn items with their tags can be returned within 30 days of shipping.
            </p>
          </div>
        </div>

        <p>
          <Link to="/products" className="btn">
            Browse the collection
          </Link>
        </p>
      </div>
    </>
  )
}
