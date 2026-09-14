import { useState, type FormEvent } from "react";
import { Check, KeyRound } from "lucide-react";
import { idPath, post, request } from "../api/client";
import type { Credential } from "../api/types";
import { useAsync } from "../hooks";
import { ErrorState, Loading, PageHeading } from "../components";

const providers = [
  {
    id: "openai",
    name: "OpenAI",
    description: "Use OpenAI models to build your learning plan.",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    description: "Use Claude models for explanations and lessons.",
  },
  {
    id: "ollama",
    name: "Ollama",
    description: "Connect models running on your own machine.",
  },
  {
    id: "youtube",
    name: "YouTube",
    description: "Find relevant learning videos with a YouTube Data API key.",
  },
];
function CredentialCard({
  provider,
  credential,
  reload,
}: {
  provider: (typeof providers)[number];
  credential?: Credential;
  reload: () => void;
}) {
  const [editing, setEditing] = useState(false),
    [key, setKey] = useState(""),
    [baseUrl, setBaseUrl] = useState(
      credential?.base_url || "http://ollama:11434",
    ),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [confirmRemove, setConfirmRemove] = useState(false),
    [replacement, setReplacement] = useState<Credential | null>(null);
  const [validated, setValidated] = useState(
    credential?.validated || credential?.validation_status === "ok",
  );
  const fieldId = `${provider.id}-${credential?.id || "new"}`;
  const run = async (action: string, fn: () => Promise<void>) => {
    setBusy(action);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "This action could not be completed.",
      );
    } finally {
      setBusy("");
    }
  };
  const save = (e: FormEvent) => {
    e.preventDefault();
    void run("save", async () => {
      const saved = await post<Credential>("/credentials", {
        provider: provider.id,
        api_key: key.trim() || (provider.id === "ollama" ? "ollama" : ""),
        ...(provider.id === "ollama" ? { base_url: baseUrl.trim() } : {}),
      });
      setKey("");
      if (credential?.id && saved.id !== credential.id) {
        setReplacement(saved);
        try {
          await request(`/credentials/${idPath(credential.id)}`, {
            method: "DELETE",
          });
        } catch {
          setEditing(false);
          setError(
            "Your new connection is saved, but the old connection could not be removed. Retry removing the old connection below.",
          );
          return;
        }
      }
      setEditing(false);
      setMessage("Connection saved.");
      reload();
    });
  };
  return (
    <article className="credential-card">
      <div className="provider-heading">
        <div
          className={`provider-icon provider-${provider.id}`}
          aria-hidden="true"
        >
          {provider.name[0]}
        </div>
        <div>
          <h2>{provider.name}</h2>
          <p>{provider.description}</p>
        </div>
      </div>
      {replacement ? (
        <div className="notice">
          <p>
            Replacement saved as •••• {replacement.masked_label?.slice(-4)}.
            Remove the old connection to finish replacing it.
          </p>
          <button
            disabled={!!busy}
            onClick={() =>
              void run("cleanup", async () => {
                await request(`/credentials/${idPath(credential!.id!)}`, {
                  method: "DELETE",
                });
                reload();
              })
            }
          >
            {busy ? "Removing…" : "Remove old connection"}
          </button>
        </div>
      ) : credential && !editing ? (
        <>
          <div className="saved-key">
            <KeyRound size={18} aria-hidden="true" />
            <span>
              {credential.masked_label
                ? `•••• ${credential.masked_label.slice(-4)}`
                : "Local connection"}
            </span>
            {credential.is_active_provider && (
              <span className="badge success">Active provider</span>
            )}
            <span className={`badge ${validated ? "success" : ""}`}>
              {validated ? (
                <>
                  <Check size={14} />
                  Connection verified
                </>
              ) : (
                "Not tested"
              )}
            </span>
          </div>
          <div className="button-row">
            <button
              className="secondary"
              disabled={!!busy || !credential.id}
              onClick={() =>
                void run("test", async () => {
                  const result = await post<{
                    validated?: boolean;
                    success?: boolean;
                    ok?: boolean;
                  }>(`/credentials/${idPath(credential.id!)}/test`);
                  const ok = result?.validated ?? result?.success ?? result?.ok;
                  setValidated(ok === true);
                  setMessage(
                    ok === true
                      ? "Connection successful."
                      : ok === false
                        ? "Connection failed. Replace your key or check your provider settings."
                        : "Test finished. Refresh Settings to see the provider status.",
                  );
                })
              }
            >
              {busy === "test" ? "Testing…" : "Test connection"}
            </button>
            <button
              className="secondary"
              disabled={!!busy}
              onClick={() => {
                setEditing(true);
                setMessage("");
              }}
            >
              Replace
            </button>
            <button
              className="quiet danger"
              disabled={!!busy || !credential.id}
              onClick={() => setConfirmRemove(true)}
            >
              Remove
            </button>
          </div>
          {!credential.id && (
            <p className="notice">
              The API must return a credential ID to enable testing and removal.
            </p>
          )}
          {confirmRemove && (
            <div className="notice">
              <p>
                Remove the {provider.name} connection? You can add it again
                later.
              </p>
              <div className="button-row">
                <button
                  className="danger-button"
                  disabled={!!busy}
                  onClick={() =>
                    void run("remove", async () => {
                      await request(`/credentials/${idPath(credential.id!)}`, {
                        method: "DELETE",
                      });
                      setKey("");
                      setConfirmRemove(false);
                      reload();
                    })
                  }
                >
                  {busy === "remove" ? "Removing…" : "Remove connection"}
                </button>
                <button
                  className="secondary"
                  disabled={!!busy}
                  onClick={() => setConfirmRemove(false)}
                >
                  Keep connection
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <form onSubmit={save}>
          <label htmlFor={`key-${fieldId}`}>
            {credential ? "New API key" : "API key"}
            {provider.id === "ollama" ? " (optional)" : ""}
          </label>
          <input
            id={`key-${fieldId}`}
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            value={key}
            required={provider.id !== "ollama"}
            onChange={(e) => setKey(e.target.value)}
            placeholder={
              provider.id === "ollama"
                ? "Leave blank for a local Ollama server"
                : "Paste your API key"
            }
            disabled={!!busy}
          />
          {provider.id === "ollama" && (
            <>
              <label htmlFor={`url-${fieldId}`}>Ollama base URL</label>
              <input
                id={`url-${fieldId}`}
                type="url"
                required
                pattern="https?://.*"
                value={baseUrl}
                disabled={!!busy}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
              <p className="field-help">
                Use http://ollama:11434 for the Docker Compose service, or
                host.docker.internal for Ollama on your host.
              </p>
            </>
          )}
          <div className="button-row">
            <button disabled={!!busy}>
              {busy === "save"
                ? "Saving…"
                : credential
                  ? "Save replacement"
                  : "Save"}
            </button>
            {credential && (
              <button
                className="secondary"
                type="button"
                disabled={!!busy}
                onClick={() => {
                  setEditing(false);
                  setKey("");
                }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      )}
      {error && <ErrorState message={error} />}
      <p className="status-message" role="status">
        {message}
      </p>
    </article>
  );
}
export function Settings() {
  const state = useAsync("credentials", (signal) =>
    request<Credential[]>("/credentials", { signal }),
  );
  return (
    <>
      <PageHeading title="Your tools for learning.">
        Connect an AI provider to create lessons, and YouTube to discover
        videos.
      </PageHeading>
      <div className="privacy-note">
        <KeyRound size={22} />
        <p>
          Keys are sent to your own MeroGuru API. After saving, only the last
          four characters are shown. Keys are never stored in this browser.
        </p>
      </div>
      {state.loading ? (
        <Loading>Checking your connections…</Loading>
      ) : state.error ? (
        <ErrorState message={state.error} retry={state.reload} />
      ) : (
        <div className="credentials-grid">
          {providers.map((provider) => {
            const credentials =
              state.data?.filter((c) => c.provider === provider.id) || [];
            return credentials.length ? (
              credentials.map((credential) => (
                <CredentialCard
                  key={`${provider.id}-${credential.id}-${credential.masked_label}`}
                  provider={provider}
                  credential={credential}
                  reload={state.reload}
                />
              ))
            ) : (
              <CredentialCard
                key={provider.id}
                provider={provider}
                reload={state.reload}
              />
            );
          })}
        </div>
      )}
    </>
  );
}
