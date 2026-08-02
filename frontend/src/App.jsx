import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

const ArrowIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M5 12h14M14 7l5 5-5 5" />
  </svg>
);

const BackIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="m15 18-6-6 6-6" />
  </svg>
);

const CheckIcon = () => (
  <svg viewBox="0 0 32 32" aria-hidden="true">
    <path d="m8.5 16.5 5 5 10-11" />
  </svg>
);

function Shell({ step, children, className = "" }) {
  return (
    <main className={`app-shell ${className}`}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <header className="topbar">
        <a className="brand" href="/" aria-label="ClosedClub — на главную">
          <span className="brand-mark">C</span>
          <span>CLOSEDCLUB</span>
        </a>
        <span className="step-indicator" aria-label={`Шаг ${step} из 3`}>
          0{step}<span>/03</span>
        </span>
      </header>
      {children}
    </main>
  );
}

function LandingPage() {
  const navigate = useNavigate();

  return (
    <Shell step={1} className="landing-shell">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span /> Закрытое сообщество</div>
          <h1>
            Капитал растёт<br />
            <em>в правильном окружении</em>
          </h1>
          <p className="hero-lead">
            Пространство для инвесторов и предпринимателей, где опыт превращается
            в решения, а сильные знакомства — в новые возможности.
          </p>
          <button className="primary-button" type="button" onClick={() => navigate("/apply")}>
            <span>Далее</span>
            <span className="button-icon"><ArrowIcon /></span>
          </button>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="orbit orbit-outer" />
          <div className="orbit orbit-inner" />
          <div className="visual-card">
            <span className="monogram">CC</span>
            <span className="card-line" />
            <span className="card-caption">Private investment circle</span>
          </div>
          <span className="visual-index">01</span>
        </div>
      </section>

      <section className="principles" aria-label="Принципы сообщества">
        <article>
          <span className="principle-number">01</span>
          <div><h2>Проверенное окружение</h2><p>Каждый участник проходит предварительный отбор.</p></div>
        </article>
        <article>
          <span className="principle-number">02</span>
          <div><h2>Практический опыт</h2><p>Обсуждаем реальные решения, сделки и стратегии.</p></div>
        </article>
        <article>
          <span className="principle-number">03</span>
          <div><h2>Конфиденциальность</h2><p>Разговоры внутри клуба остаются внутри клуба.</p></div>
        </article>
      </section>
    </Shell>
  );
}

const initialForm = {
  first_name: "",
  last_name: "",
  occupation: "",
  monthly_income: "",
  city: "",
};

function ApplicationPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const updateField = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    if (error) setError("");
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await fetch("/api/applications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Init-Data": window.Telegram?.WebApp?.initData ?? "",
        },
        body: JSON.stringify({
          ...form,
          monthly_income: Number(form.monthly_income),
        }),
      });

      if (response.status === 401) {
        throw new Error("telegram_auth");
      }

      if (response.status === 429) {
        throw new Error("rate_limit");
      }

      if (!response.ok) {
        throw new Error("Не удалось отправить заявку");
      }

      navigate("/success", { replace: true });
    } catch (submissionError) {
      if (submissionError.message === "telegram_auth") {
        setError("Откройте эту форму через Telegram-бота и попробуйте ещё раз.");
      } else if (submissionError.message === "rate_limit") {
        setError("Вы уже отправляли заявку. Мы обязательно её рассмотрим.");
      } else {
        setError("Не получилось отправить заявку. Проверьте соединение и попробуйте ещё раз.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Shell step={2} className="form-shell">
      <section className="form-layout">
        <div className="form-intro">
          <button className="back-button" type="button" onClick={() => navigate(-1)}>
            <BackIcon /> Назад
          </button>
          <div className="eyebrow"><span /> Заявка на вступление</div>
          <h1>Давайте<br /><em>познакомимся</em></h1>
          <p>
            Ответьте на несколько вопросов. Мы изучим заявку и свяжемся с вами
            через Telegram.
          </p>
          <div className="privacy-note">
            <span className="privacy-dot" />
            Данные используются только для рассмотрения заявки
          </div>
        </div>

        <form className="application-form" onSubmit={submit}>
          <div className="field-row">
            <label>
              <span>Имя</span>
              <input
                name="first_name"
                value={form.first_name}
                onChange={updateField}
                autoComplete="given-name"
                maxLength="80"
                placeholder="Александр"
                required
              />
            </label>
            <label>
              <span>Фамилия</span>
              <input
                name="last_name"
                value={form.last_name}
                onChange={updateField}
                autoComplete="family-name"
                maxLength="80"
                placeholder="Иванов"
                required
              />
            </label>
          </div>

          <label>
            <span>Род деятельности</span>
            <input
              name="occupation"
              value={form.occupation}
              onChange={updateField}
              autoComplete="organization-title"
              maxLength="160"
              placeholder="Предприниматель, инвестор, руководитель..."
              required
            />
          </label>

          <div className="field-row">
            <label>
              <span>Доход в месяц</span>
              <div className="input-with-suffix">
                <input
                  name="monthly_income"
                  value={form.monthly_income}
                  onChange={updateField}
                  type="number"
                  inputMode="numeric"
                  min="1"
                  max="10000000000"
                  placeholder="500 000"
                  required
                />
                <span>₽</span>
              </div>
            </label>
            <label>
              <span>Город</span>
              <input
                name="city"
                value={form.city}
                onChange={updateField}
                autoComplete="address-level2"
                maxLength="120"
                placeholder="Москва"
                required
              />
            </label>
          </div>

          {error && <p className="form-error" role="alert">{error}</p>}

          <button className="submit-button" type="submit" disabled={submitting}>
            <span>{submitting ? "Отправляем…" : "Оставить заявку"}</span>
            <ArrowIcon />
          </button>
          <p className="consent-copy">
            Нажимая кнопку, вы соглашаетесь на обработку указанных данных для рассмотрения заявки.
          </p>
        </form>
      </section>
    </Shell>
  );
}

function SuccessPage() {
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <Shell step={3} className="success-shell">
      <section className="success-content">
        <div className="success-symbol">
          <span className="success-ring" />
          <span className="check-circle"><CheckIcon /></span>
        </div>
        <div className="eyebrow"><span /> Заявка принята</div>
        <h1>Ваша заявка<br /><em>отправлена</em></h1>
        <p>
          Мы внимательно её рассмотрим и свяжемся с вами через этого же
          Telegram-бота.
        </p>
        <button className="secondary-button" type="button" onClick={() => navigate("/")}>
          Вернуться на главную
        </button>
      </section>
      <footer className="success-footer">
        <span>ClosedClub</span>
        <span>Private investment community</span>
      </footer>
    </Shell>
  );
}

export default function App() {
  useEffect(() => {
    const telegram = window.Telegram?.WebApp;
    if (telegram) {
      telegram.ready();
      telegram.expand();
    }
  }, []);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/apply" element={<ApplicationPage />} />
      <Route path="/success" element={<SuccessPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
