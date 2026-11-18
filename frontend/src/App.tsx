import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type {
  Campaign,
  CampaignCreateResult,
  LocalOffer,
  LocalStream,
  Offer,
} from "./api";
import "./App.css";

type Tab = "create" | "editor";

export default function App() {
  const [tab, setTab] = useState<Tab>("create");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div className="app">
      <header className="header">
        <h1>Keitaro</h1>
        <nav className="tabs">
          <button
            className={tab === "create" ? "tab active" : "tab"}
            onClick={() => setTab("create")}
          >
            Создаватор
          </button>
          <button
            className={tab === "editor" ? "tab active" : "tab"}
            onClick={() => setTab("editor")}
          >
            Редактор
          </button>
        </nav>
      </header>

      {error && (
        <div className="banner error" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      {tab === "create" ? (
        <CreateCampaign busy={busy} setBusy={setBusy} setError={setError} />
      ) : (
        <CampaignEditor busy={busy} setBusy={setBusy} setError={setError} />
      )}
    </div>
  );
}

function CreateCampaign({
  busy,
  setBusy,
  setError,
}: {
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string | null) => void;
}) {
  const [name, setName] = useState("");
  const [geo, setGeo] = useState("AU");
  const [offerId, setOfferId] = useState("");
  const [offerQuery, setOfferQuery] = useState("");
  const [offers, setOffers] = useState<Offer[]>([]);
  const [result, setResult] = useState<CampaignCreateResult | null>(null);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!offerQuery.trim()) {
        setOffers([]);
        return;
      }
      try {
        setOffers(await api.searchOffers(offerQuery.trim()));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [offerQuery, setError]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const id = Number(offerId);
    if (!offerId.trim() || !Number.isInteger(id) || id <= 0) {
      setError("Введите ID оффера");
      return;
    }
    if (!/^[A-Za-z]{2}$/.test(geo.trim())) {
      setError("Гео-код — две латинские буквы, например AU");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const created = await api.createCampaign({
        name: name.trim(),
        geo: geo.trim(),
        offer_id: id,
      });
      setResult(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Создать кампанию</h2>
      <p className="muted">
        Два потока: указанная страна уходит на Google, остальные — на оффер.
        Домен берётся первый из Keitaro, группа и источник — с «fortest» в
        названии, если они не заданы в .env.
      </p>

      <form className="form" onSubmit={onSubmit}>
        <label>
          Название
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="test_campaign"
          />
        </label>
        <label>
          Гео-код
          <input
            value={geo}
            onChange={(e) => setGeo(e.target.value.toUpperCase())}
            required
            minLength={2}
            maxLength={2}
            pattern="[A-Za-z]{2}"
            placeholder="AU"
          />
        </label>
        <label>
          ID оффера
          <input
            type="number"
            min={1}
            required
            value={offerId}
            onChange={(e) => setOfferId(e.target.value)}
            placeholder="10184"
          />
        </label>
        <label>
          Поиск по названию
          <input
            value={offerQuery}
            onChange={(e) => setOfferQuery(e.target.value)}
            placeholder="часть названия"
          />
        </label>
        <label>
          Найденные
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) setOfferId(e.target.value);
            }}
          >
            <option value="">Подставить ID</option>
            {offers.map((o) => (
              <option key={o.id} value={o.id}>
                #{o.id} — {o.name}
              </option>
            ))}
          </select>
        </label>
        <button className="primary" disabled={busy} type="submit">
          {busy ? "Создаём…" : "Создать кампанию"}
        </button>
      </form>

      {result && (
        <div className="banner success">
          <strong>Кампания #{result.id}</strong> создана.
          <div className="meta-grid">
            <span>Alias: {result.alias || "—"}</span>
            <span>Domain ID: {result.domain_id}</span>
            <span>Group ID: {result.group_id}</span>
            <span>Source ID: {result.traffic_source_id}</span>
            <span>Google stream: {result.google_stream_id}</span>
            <span>Offers stream: {result.offers_stream_id}</span>
            {result.campaign_url && (
              <a href={result.campaign_url} target="_blank" rel="noreferrer">
                {result.campaign_url}
              </a>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function CampaignEditor({
  busy,
  setBusy,
  setError,
}: {
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string | null) => void;
}) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignId, setCampaignId] = useState<number | "">("");
  const [streams, setStreams] = useState<LocalStream[]>([]);
  const [fetchNote, setFetchNote] = useState<string | null>(null);
  const [offerQuery, setOfferQuery] = useState("");
  const [offers, setOffers] = useState<Offer[]>([]);
  const [offerIdInput, setOfferIdInput] = useState("");

  useEffect(() => {
    api
      .listCampaigns()
      .then(setCampaigns)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [setError]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!offerQuery.trim()) {
        setOffers([]);
        return;
      }
      try {
        setOffers(await api.searchOffers(offerQuery.trim()));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [offerQuery, setError]);

  const offerStreams = useMemo(
    () => streams.filter((s) => s.has_offers),
    [streams],
  );
  const emptyStreams = useMemo(
    () => streams.filter((s) => !s.has_offers),
    [streams],
  );

  function offerIdToAdd(): number | null {
    const id = Number(offerIdInput);
    if (!offerIdInput.trim() || !Number.isInteger(id) || id <= 0) return null;
    return id;
  }

  async function run(action: () => Promise<LocalStream | LocalStream[]>) {
    setBusy(true);
    setError(null);
    setFetchNote(null);
    try {
      const result = await action();
      if (Array.isArray(result)) {
        setStreams(result);
      } else {
        setStreams((prev) => prev.map((s) => (s.id === result.id ? result : s)));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function fetchStreams() {
    if (!campaignId) {
      setError("Выберите кампанию");
      return;
    }
    setBusy(true);
    setError(null);
    setFetchNote(null);
    try {
      const result = await api.fetchStreams(Number(campaignId));
      setStreams(result);
      const dirty = result.filter((s) => s.is_dirty);
      if (dirty.length) {
        const names = dirty.map((s) => s.name).join(", ");
        setFetchNote(
          `Черновик не перезаписан: ${names}. Сначала Push to Keitaro или Cancel, потом Fetch снова.`,
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Редактор офферов</h2>
      <p className="muted">
        Fetch Streams забирает потоки. Правки остаются локальными, пока не
        нажата Push to Keitaro. Cancel возвращает последний опубликованный
        снимок. Жёлтый блок — черновик.
      </p>

      <div className="toolbar">
        <label className="grow">
          Кампания
          <select
            value={campaignId}
            onChange={(e) => {
              setCampaignId(e.target.value ? Number(e.target.value) : "");
              setStreams([]);
              setFetchNote(null);
            }}
          >
            <option value="">Выберите кампанию</option>
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>
        </label>
        <button className="primary" disabled={busy} onClick={fetchStreams}>
          Fetch Streams
        </button>
      </div>

      {fetchNote && <p className="note">{fetchNote}</p>}

      <div className="toolbar">
        <label className="grow">
          ID оффера
          <input
            type="number"
            min={1}
            value={offerIdInput}
            onChange={(e) => setOfferIdInput(e.target.value)}
            placeholder="ID для Add offer"
          />
        </label>
        <label className="grow">
          Поиск
          <input
            value={offerQuery}
            onChange={(e) => setOfferQuery(e.target.value)}
            placeholder="часть названия"
          />
        </label>
        <label className="grow">
          Найденные
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) setOfferIdInput(e.target.value);
            }}
          >
            <option value="">Подставить ID</option>
            {offers.map((o) => (
              <option key={o.id} value={o.id}>
                #{o.id} — {o.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {emptyStreams.length > 0 && (
        <div className="stream-shells">
          {emptyStreams.map((s) => (
            <div key={s.id} className="stream-card shell">
              <div className="stream-title">
                <strong>{s.name}</strong>
                <span className="muted">без офферов</span>
              </div>
              <p className="muted small">
                Поток #{s.keitaro_stream_id}. Фильтры и редирект не разбираем.
              </p>
            </div>
          ))}
        </div>
      )}

      {offerStreams.map((stream) => (
        <StreamEditor
          key={stream.id}
          stream={stream}
          busy={busy}
          onAdd={() => {
            const id = offerIdToAdd();
            if (!id) {
              setError("Введите ID оффера");
              return;
            }
            return run(() => api.addOffer(stream.id, id));
          }}
          onRemove={(offer) => run(() => api.removeOffer(stream.id, offer.id))}
          onBringBack={(offer) => run(() => api.bringBack(stream.id, offer.id))}
          onPin={(offer, pinned, share) =>
            run(() => api.pinOffer(stream.id, offer.id, pinned, share))
          }
          onPush={() => run(() => api.pushStream(stream.id))}
          onCancel={() => run(() => api.cancelStream(stream.id))}
        />
      ))}

      {!streams.length && (
        <p className="muted">Потоков нет. Выберите кампанию и нажмите Fetch Streams.</p>
      )}
    </section>
  );
}

function ShareField({
  offer,
  busy,
  onCommit,
}: {
  offer: LocalOffer;
  busy: boolean;
  onCommit: (share: number) => void;
}) {
  const [value, setValue] = useState(String(offer.share));
  const wasBusy = useRef(false);

  useEffect(() => {
    setValue(String(offer.share));
  }, [offer.share]);

  useEffect(() => {
    if (wasBusy.current && !busy) {
      setValue(String(offer.share));
    }
    wasBusy.current = busy;
  }, [busy, offer.share]);

  function commit() {
    if (value.trim() === "" || Number(value) === offer.share) {
      setValue(String(offer.share));
      return;
    }
    const next = Number(value);
    if (!Number.isInteger(next) || next < 0 || next > 100) {
      setValue(String(offer.share));
      return;
    }
    onCommit(next);
  }

  return (
    <input
      type="number"
      min={0}
      max={100}
      disabled={busy || !offer.is_pinned || offer.status !== "active"}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          e.currentTarget.blur();
        }
      }}
      title={offer.is_pinned ? "Доля зафиксирована. Enter или уход из поля сохраняет её" : "Сначала включите pin"}
    />
  );
}

function StreamEditor({
  stream,
  busy,
  onAdd,
  onRemove,
  onBringBack,
  onPin,
  onPush,
  onCancel,
}: {
  stream: LocalStream;
  busy: boolean;
  onAdd: () => void | Promise<void>;
  onRemove: (o: LocalOffer) => void;
  onBringBack: (o: LocalOffer) => void;
  onPin: (o: LocalOffer, pinned: boolean, share?: number) => void;
  onPush: () => void;
  onCancel: () => void;
}) {
  const activeShare = stream.offers
    .filter((o) => o.status === "active")
    .reduce((sum, o) => sum + o.share, 0);

  return (
    <div className={`stream-card ${stream.is_dirty ? "dirty" : ""}`}>
      <div className="stream-title">
        <strong>
          {stream.name}
          <span className="muted"> · #{stream.keitaro_stream_id}</span>
        </strong>
        <span className="muted">
          {activeShare}%{stream.is_dirty ? " · не опубликовано" : ""}
        </span>
      </div>

      <div className="offers-table">
        <div className="offers-head">
          <span>Оффер</span>
          <span>Доля</span>
          <span>Pin</span>
          <span></span>
        </div>
        {stream.offers.map((offer) => (
          <div
            key={offer.id}
            className={`offers-row ${offer.status === "removed" ? "removed" : ""}`}
          >
            <div>
              <div>#{offer.keitaro_offer_id}</div>
              <div className="muted small">{offer.name}</div>
            </div>
            <div>
              <ShareField
                offer={offer}
                busy={busy}
                onCommit={(share) => onPin(offer, true, share)}
              />
            </div>
            <div>
              <input
                type="checkbox"
                checked={offer.is_pinned}
                disabled={busy || offer.status !== "active"}
                onChange={(e) => onPin(offer, e.target.checked, offer.share)}
              />
            </div>
            <div className="row-actions">
              {offer.status === "active" ? (
                <button disabled={busy} onClick={() => onRemove(offer)}>
                  Remove
                </button>
              ) : (
                <button disabled={busy} onClick={() => onBringBack(offer)}>
                  Bring back
                </button>
              )}
            </div>
          </div>
        ))}
        {!stream.offers.length && <p className="muted small">В потоке нет офферов.</p>}
      </div>

      <div className="toolbar">
        <button disabled={busy} onClick={() => void onAdd()}>
          Add offer
        </button>
        <button className="primary" disabled={busy || !stream.is_dirty} onClick={onPush}>
          Push to Keitaro
        </button>
        <button disabled={busy || !stream.is_dirty} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
