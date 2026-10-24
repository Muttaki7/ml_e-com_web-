"use client";

import { useEffect, useMemo, useState } from "react";
import { metaApi } from "@/lib/api";
import { Phone } from "lucide-react";

export interface Country {
  code: string;
  name: string;
  dial_code: string;
  currency: string;
  currency_symbol: string;
}

let cachedCountries: Country[] | null = null;

/** Load (and cache) the country list served by the backend. */
export async function loadCountries(): Promise<Country[]> {
  if (!cachedCountries) {
    const { data } = await metaApi.countries();
    cachedCountries = [...(data as Country[])].sort((a, b) => a.name.localeCompare(b.name));
  }
  return cachedCountries;
}

interface IntlPhoneInputProps {
  /** Full E.164 value, e.g. +14155552671. Updated on every change. */
  value: string;
  onChange: (e164: string) => void;
  /** Alpha-2 country used for the initial dial code. */
  defaultCountry?: string;
  required?: boolean;
  placeholder?: string;
}

/**
 * Country dial-code select + national number input that composes an E.164
 * phone number for the backend (which validates it with libphonenumber).
 */
export default function IntlPhoneInput({
  value,
  onChange,
  defaultCountry = "US",
  required = true,
  placeholder = "415 555 2671",
}: IntlPhoneInputProps) {
  const [countries, setCountries] = useState<Country[]>([]);
  const [dial, setDial] = useState("+1");
  const [national, setNational] = useState("");

  useEffect(() => {
    loadCountries().then((list) => {
      setCountries(list);
      const preferred = list.find((c) => c.code === defaultCountry) || list.find((c) => c.dial_code === "+1");
      if (!value && preferred) setDial(preferred.dial_code);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When the parent value changes externally (e.g. pre-filled address),
  // re-derive dial + national parts.
  useEffect(() => {
    if (!countries.length || !value) return;
    const match = countries
      .filter((c) => value.startsWith(c.dial_code.replace(/[^\d+]/g, "")))
      .sort((a, b) => b.dial_code.length - a.dial_code.length)[0];
    if (match) {
      setDial(match.dial_code);
      setNational(value.slice(match.dial_code.replace(/[^\d]/g, "").length + 1));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countries]);

  const dialOptions = useMemo(() => countries, [countries]);

  function handleDialChange(nextDial: string) {
    setDial(nextDial);
    const digits = national.replace(/\D/g, "");
    onChange(digits ? nextDial + digits : "");
  }

  function handleNationalChange(nextNational: string) {
    const digits = nextNational.replace(/[^\d]/g, "").slice(0, 14);
    setNational(digits);
    onChange(digits ? dial + digits : "");
  }

  return (
    <div className="flex gap-2">
      <select
        value={dial}
        onChange={(e) => handleDialChange(e.target.value)}
        className="input !w-auto shrink-0"
        aria-label="Country code"
        required={required}
      >
        {dialOptions.map((c) => (
          <option key={c.code} value={c.dial_code}>
            {c.code} {c.dial_code}
          </option>
        ))}
        {!dialOptions.length && <option value={dial}>{dial}</option>}
      </select>
      <div className="relative flex-1">
        <Phone size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="tel"
          value={national}
          onChange={(e) => handleNationalChange(e.target.value)}
          className="input w-full !pl-10"
          placeholder={placeholder}
          required={required}
          minLength={4}
          maxLength={14}
        />
      </div>
    </div>
  );
}
