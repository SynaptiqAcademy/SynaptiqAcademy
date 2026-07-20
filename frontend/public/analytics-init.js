// PostHog analytics initialization (AUTH-004: moved out of inline script)
(function(t, e) {
  var o, n, p, r;
  if (!e.__SV) {
    window.posthog = e;
    e._i = [];
    e.init = function(i, s, a) {
      function g(t, e) {
        var o = e.split(".");
        if (o.length === 2) { t = t[o[0]]; e = o[1]; }
        t[e] = function() { t.push([e].concat(Array.prototype.slice.call(arguments, 0))); };
      }
      p = t.createElement("script");
      p.type = "text/javascript";
      p.crossOrigin = "anonymous";
      p.async = true;
      p.src = s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") + "/static/array.js";
      r = t.getElementsByTagName("script")[0];
      r.parentNode.insertBefore(p, r);
      var u = e;
      if (a !== undefined) { u = e[a] = []; } else { a = "posthog"; }
      u.people = u.people || [];
      u.toString = function(t) {
        var e = "posthog";
        if (a !== "posthog") e += "." + a;
        if (!t) e += " (stub)";
        return e;
      };
      u.people.toString = function() { return u.toString(1) + ".people (stub)"; };
      o = "init me ws ys ps bs capture je Di ks register register_once register_for_session unregister unregister_for_session Ps getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty Es $s createPersonProfile Is opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing Ss debug xs getPageViewId captureTraceFeedback captureTraceMetric".split(" ");
      for (n = 0; n < o.length; n++) g(u, o[n]);
      e._i.push([i, s, a]);
    };
    e.__SV = 1;
  }
})(document, window.posthog || []);

// GDPR gate: PostHog must not run (no init, no cookies, no network calls)
// until the user has explicitly granted Analytics consent via the cookie
// banner. See src/lib/cookieConsent.js — this file has no build step, so
// it reads the same localStorage key directly instead of importing it.
(function () {
  var POSTHOG_KEY = "phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs";
  var CONSENT_KEY = "synaptiq_consent_v1";
  var initialized = false;

  function analyticsAllowed() {
    try {
      var record = JSON.parse(localStorage.getItem(CONSENT_KEY) || "null");
      return !!(record && record.prefs && record.prefs.analytics);
    } catch (e) {
      return false;
    }
  }

  // opt_in_capturing/opt_out_capturing are commands, not queries — they're
  // safe to call idempotently and, like init(), are queued by the stub and
  // correctly replayed once the real library loads, regardless of timing.
  // (has_opted_out_capturing() is a query and is NOT reliably synchronous
  // even inside PostHog's own `loaded` callback, so we deliberately never
  // branch on it — we just state the desired outcome every time.)
  function applyOptState() {
    if (analyticsAllowed()) {
      if (posthog.opt_in_capturing) posthog.opt_in_capturing();
    } else if (posthog.opt_out_capturing) {
      posthog.opt_out_capturing();
    }
  }

  function sync() {
    if (analyticsAllowed() && !initialized) {
      initialized = true;
      posthog.init(POSTHOG_KEY, {
        api_host: "https://us.i.posthog.com",
        person_profiles: "identified_only",
        session_recording: {
          recordCrossOriginIframes: true,
          capturePerformance: false,
        },
        loaded: applyOptState,
      });
    }
    if (initialized) applyOptState();
  }

  sync();
  // Same-tab: cookieConsent.js dispatches this after every save/reset.
  window.addEventListener("synaptiq:consent-changed", sync);
  // Cross-tab: native storage event fires in other open tabs.
  window.addEventListener("storage", function (e) {
    if (e.key === CONSENT_KEY) sync();
  });
})();
