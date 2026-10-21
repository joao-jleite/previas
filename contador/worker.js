// Sinal das prévias: registra visita (beacon do JS da página) e clique em "quero este site"
// (redireciona ao WhatsApp do João). Sem cookie, sem IP: só slug, tipo e hora.
const WHATS = "5511961551602";
const CORS = { "Access-Control-Allow-Origin": "https://joao-jleite.github.io" };

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const slug = (u.searchParams.get("s") || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 80);
    const tipo = u.pathname === "/v" ? "visita" : u.pathname === "/w" ? "clique" : "";
    // Robôs (pré-visualização de link, antivírus de e-mail) não contam
    const robo = /bot|crawl|spider|preview|scan|headless|facebookexternalhit|whatsapp/i.test(req.headers.get("user-agent") || "");
    if (tipo && slug && !robo) {
      try { await env.DB.prepare("INSERT INTO eventos (slug, tipo) VALUES (?, ?)").bind(slug, tipo).run(); }
      catch (e) { /* falha no registro nunca impede o redirecionamento */ }
    }
    if (tipo === "clique") {
      const texto = (u.searchParams.get("t") || "Olá, João. Vi a prévia do meu site e quero saber como colocá-lo no ar.").slice(0, 300);
      return Response.redirect(`https://wa.me/${WHATS}?text=${encodeURIComponent(texto)}`, 302);
    }
    return new Response(null, { status: 204, headers: CORS });
  },
};
