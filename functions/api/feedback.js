/**
 * Cloudflare Pages Function: příjem zpráv z formuláře /napiste-mi/.
 * Ověří Turnstile (ochrana proti spamu) a zprávu přepošle e-mailem přes
 * Resend. Nasazuje se automaticky s webem (adresář functions/ čte Pages).
 *
 * Potřebné proměnné v Cloudflare Pages (Settings → Environment variables):
 *   TURNSTILE_SECRET_KEY ... secret z Turnstile widgetu
 *   RESEND_API_KEY       ... API klíč z resend.com (free tier)
 *   FEEDBACK_TO          ... e-mail, kam mají zprávy chodit
 * Ve frontendu k tomu patří build proměnná PUBLIC_TURNSTILE_SITE_KEY.
 */

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

export async function onRequestPost({ request, env }) {
  let data;
  try {
    data = await request.json();
  } catch {
    return json({ ok: false, error: 'Neplatný požadavek.' }, 400);
  }

  // honeypot: pole „website" vyplňují jen boti – tiše zahodit jako úspěch
  if (data.website) return json({ ok: true });

  const message = String(data.message || '').trim();
  const name = String(data.name || '').trim().slice(0, 200);
  const email = String(data.email || '').trim().slice(0, 200);
  if (!message) return json({ ok: false, error: 'Zpráva je prázdná.' }, 400);
  if (message.length > 5000) return json({ ok: false, error: 'Zpráva je příliš dlouhá (max 5000 znaků).' }, 400);

  const verify = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      secret: env.TURNSTILE_SECRET_KEY,
      response: data.turnstile || '',
      remoteip: request.headers.get('CF-Connecting-IP'),
    }),
  });
  const outcome = await verify.json();
  if (!outcome.success) {
    return json({ ok: false, error: 'Ověření proti spamu se nezdařilo, zkuste to prosím znovu.' }, 403);
  }

  const sent = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${env.RESEND_API_KEY}`,
    },
    body: JSON.stringify({
      from: 'To hýbe trhy <onboarding@resend.dev>',
      to: [env.FEEDBACK_TO],
      reply_to: email || undefined,
      subject: `Zpráva z tohybetrhy${name ? ` – ${name}` : ''}`,
      text: `Jméno: ${name || '—'}\nE-mail: ${email || '—'}\n\n${message}`,
    }),
  });
  if (!sent.ok) {
    return json({ ok: false, error: 'Odeslání se nezdařilo, zkuste to prosím později.' }, 502);
  }
  return json({ ok: true });
}
