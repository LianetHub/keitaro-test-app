const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export type Campaign = {
  id: number;
  name: string;
  alias?: string | null;
  domain?: string | null;
  group?: string | null;
  state?: string | null;
};

export type Offer = {
  id: number;
  name: string;
  state?: string | null;
  country?: string[] | null;
};

export type LocalOffer = {
  id: number;
  keitaro_offer_id: number;
  name: string;
  share: number;
  is_pinned: boolean;
  status: string;
};

export type LocalStream = {
  id: number;
  campaign_id: number;
  keitaro_stream_id: number;
  name: string;
  has_offers: boolean;
  is_dirty: boolean;
  offers: LocalOffer[];
};

export type CampaignCreateResult = {
  id: number;
  name: string;
  alias?: string | null;
  domain_id?: number | null;
  group_id?: number | null;
  traffic_source_id?: number | null;
  google_stream_id?: number | null;
  offers_stream_id?: number | null;
  campaign_url?: string | null;
};

export const api = {
  listCampaigns: () => request<Campaign[]>("/api/campaigns"),
  createCampaign: (body: { name: string; geo: string; offer_id: number }) =>
    request<CampaignCreateResult>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  searchOffers: (q: string) =>
    request<Offer[]>(`/api/meta/offers?q=${encodeURIComponent(q)}&limit=40`),
  fetchStreams: (campaignId: number) =>
    request<LocalStream[]>(`/api/campaigns/${campaignId}/streams/fetch`, {
      method: "POST",
    }),
  addOffer: (streamId: number, offerId: number) =>
    request<LocalStream>(`/api/campaigns/streams/${streamId}/offers`, {
      method: "POST",
      body: JSON.stringify({ offer_id: offerId }),
    }),
  removeOffer: (streamId: number, offerId: number) =>
    request<LocalStream>(`/api/campaigns/streams/${streamId}/offers/${offerId}`, {
      method: "DELETE",
    }),
  bringBack: (streamId: number, offerId: number) =>
    request<LocalStream>(
      `/api/campaigns/streams/${streamId}/offers/${offerId}/bring-back`,
      { method: "POST" },
    ),
  pinOffer: (streamId: number, offerId: number, isPinned: boolean, share?: number) =>
    request<LocalStream>(`/api/campaigns/streams/${streamId}/offers/${offerId}/pin`, {
      method: "POST",
      body: JSON.stringify({ is_pinned: isPinned, share }),
    }),
  pushStream: (streamId: number) =>
    request<LocalStream>(`/api/campaigns/streams/${streamId}/push`, {
      method: "POST",
    }),
  cancelStream: (streamId: number) =>
    request<LocalStream>(`/api/campaigns/streams/${streamId}/cancel`, {
      method: "POST",
    }),
  health: () => request<{ status: string }>("/api/health"),
};
