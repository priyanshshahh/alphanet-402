/**
 * Pitch deck demo slide: YouTube embed ID, direct file URL, or null.
 * Set `VITE_PITCH_DEMO_VIDEO_URL` in `.env` (e.g. YouTube watch or youtu.be link).
 */
export function parsePitchDemoVideoUrl(raw) {
  const url = (raw || "").trim();
  if (!url) return { kind: "none", href: null, youtubeId: null };

  if (/\.(mp4|webm|ogg)(\?|$)/i.test(url)) {
    return { kind: "file", href: url, youtubeId: null };
  }

  try {
    const u = new URL(url, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    const host = u.hostname.replace(/^www\./, "");

    if (host === "youtu.be") {
      const id = u.pathname.replace(/^\//, "").split("/")[0];
      return id ? { kind: "youtube", href: url, youtubeId: id } : { kind: "none", href: null, youtubeId: null };
    }
    if (host.endsWith("youtube.com") || host.endsWith("youtube-nocookie.com")) {
      const v = u.searchParams.get("v");
      if (v) return { kind: "youtube", href: url, youtubeId: v };
      const m = u.pathname.match(/\/embed\/([^/?]+)/);
      if (m) return { kind: "youtube", href: url, youtubeId: m[1] };
    }
    if (host.endsWith("loom.com")) {
      const share = u.pathname.match(/\/share\/([^/]+)/);
      if (share) {
        return {
          kind: "iframe",
          href: `https://www.loom.com/embed/${share[1]}`,
          youtubeId: null,
        };
      }
      if (u.pathname.includes("/embed/")) {
        return { kind: "iframe", href: url, youtubeId: null };
      }
      return { kind: "iframe", href: url, youtubeId: null };
    }
  } catch {
    return { kind: "none", href: null, youtubeId: null };
  }

  return { kind: "none", href: null, youtubeId: null };
}
