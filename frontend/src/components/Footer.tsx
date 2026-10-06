import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <h4>Campus Customs</h4>
          <p>57 Broadway, New Haven, CT 06511</p>
          <p>Officially licensed Yale apparel</p>
        </div>
        <div>
          <h4>Shop</h4>
          <Link to="/products">All products</Link>
          <Link to="/about">About us</Link>
        </div>
        <div>
          <h4>Help</h4>
          <p>
            Questions about an order?{' '}
            <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
          </p>
          <p>Unworn items with tags can be returned within 30 days of shipping.</p>
        </div>
      </div>
      <div className="container footer-bottom">
        © {new Date().getFullYear()} Campus Customs · Class project demo for AI Foundations for Managers
      </div>
    </footer>
  )
}
