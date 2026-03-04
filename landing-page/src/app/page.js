"use client";

import React, { useState, useEffect } from 'react';
import styles from './page.module.css';

const LiveSavingsCounter = () => {
  const [dollars, setDollars] = useState(1428.70);
  const [gb, setGb] = useState(2857.4);

  useEffect(() => {
    const interval = setInterval(() => {
      setDollars(prev => prev + 0.0042);
      setGb(prev => prev + 0.0087);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`${styles.liveCounter} glass`}>
      <div className={styles.counterItem}>
        <span className={styles.counterLabel}>Projected Monthly Gravity</span>
        <span className={`${styles.counterValue} gradient-text`}>${dollars.toFixed(2)}</span>
      </div>
      <div className={styles.counterDivider}></div>
      <div className={styles.counterItem}>
        <span className={styles.counterLabel}>Information Fact Extracted</span>
        <span className={styles.counterValue}>{gb.toFixed(1)} GB</span>
      </div>
    </div>
  );
};

export default function LandingPage() {
  return (
    <main className={styles.main}>
      {/* Background Glows */}
      <div className={styles.glow1}></div>
      <div className={styles.glow2}></div>

      {/* Navigation */}
      <nav className={`${styles.nav} glass`}>
        <div className={styles.logo}>
          <span className="gradient-text">APΩ</span> BalanceHub
        </div>
        <div className={styles.navLinks}>
          <a href="#manifesto">Manifesto</a>
          <a href="#breakthrough">§4287 Core</a>
          <a href="#dashboard">Command Center</a>
          <button className={styles.ctaSmall}>Join The Mesh</button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={`${styles.content} animate-fade`}>
          <h1 className={styles.title}>
            The Future of <br />
            <span className="gradient-text">Autonomous AI Governance</span>
          </h1>
          <p className={styles.subtitle}>
            Empowering the digital mesh with zero-cost, high-gravity autonomy.
            Free ≡ Good ≡ Maximum Gravity.
          </p>
          <LiveSavingsCounter />
          <div className={styles.ctaGroup}>
            <button className={styles.ctaPrimary}>Enter APΩ Portal</button>
            <button className={styles.ctaSecondary}>Read Sealed Spec</button>
          </div>
        </div>
      </section>

      {/* Breakthrough Section (§4287) */}
      <section id="breakthrough" className={styles.section}>
        <div className={`${styles.card} glass animate-fade delay-1`}>
          <h2 className="gradient-text">HyperAI Compression §4287</h2>
          <p>
            Our proprietary <strong>Information Purification</strong> engine has achieved a
            monumental <strong>100% compression ratio</strong> on 1GB industrial datasets.
          </p>
          <div className={styles.stats}>
            <div className={styles.statItem}>
              <h3>1024MB</h3>
              <span>Raw Stress Log</span>
            </div>
            <div className={styles.statArrow}>→</div>
            <div className={styles.statItem}>
              <h3>600B</h3>
              <span>Purified Fact</span>
            </div>
          </div>
          <p className={styles.caption}>Verified by the Monotonic Search Theorem: D<sub>k+1</sub> ≤ D<sub>k</sub></p>
        </div>
      </section>

      {/* Manifesto Section */}
      <section id="manifesto" className={styles.section}>
        <div className={styles.manifestoContent}>
          <h2>The Manifesto</h2>
          <p>We believe in a digital reality where autonomy is a right, not a subscription. BalanceHub là điểm neo cho một mạng lưới tự phục hồi và tự quản trị.</p>
          <ul className={styles.pillars}>
            <li>🛡️ <strong>Safety First</strong>: Fail-closed governance.</li>
            <li>🔭 <strong>Long-term Vision</strong>: 2-year stability baseline.</li>
            <li>📊 <strong>Data-Driven</strong>: Every node audit-verified.</li>
            <li>⚠️ <strong>Risk Managed</strong>: Real-time drift detection.</li>
          </ul>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>© 2026 Alpha_Prime_Omega. Built for the Infinite Mesh.</p>
      </footer>
    </main>
  );
}
