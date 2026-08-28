/**
 * Suscripciones a Supabase Realtime (§8.3 de la guía).
 *
 * Sustituye al sondeo de 5 s de la fase local. La diferencia no es solo de
 * eficiencia: el sondeo introduce hasta 5 s de retraso en una plataforma donde
 * el dato que llega tarde es una ambulancia que sale tarde.
 *
 * ── Qué NO hace ─────────────────────────────────────────────────────────────
 * Realtime aquí es solo una SEÑAL de "algo cambió". Los datos siguen viniendo
 * por REST desde el API Gateway (§9: Frontend → API Gateway → Lambda → Supabase).
 * Al recibir un evento se invalida la query de TanStack Query correspondiente y
 * es esta la que vuelve a pedir por HTTP.
 *
 * Se hace así a propósito y no leyendo el payload del evento: la fila que viaja
 * en el WAL es la de la base de datos (snake_case, sin los campos derivados que
 * añade el servicio). Mezclar esa forma con la de la API llevaría a dos
 * representaciones distintas del mismo objeto en pantalla.
 *
 * ── Requisitos del lado servidor ────────────────────────────────────────────
 * Las tablas deben estar en la publicación `supabase_realtime` con REPLICA
 * IDENTITY FULL (database/rls/004_realtime.sql) y su esquema expuesto en la
 * API del proyecto. Realtime respeta RLS: cada suscriptor recibe únicamente los
 * cambios de las filas que su política de SELECT le permite ver.
 */
import type { RealtimeChannel } from '@supabase/supabase-js'
import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabase'

/** Estado de la conexión, para poder mostrarlo en pantalla. */
export type RealtimeStatus = 'connecting' | 'connected' | 'error'

export interface RealtimeTable {
  schema: string
  table: string
  /** Filtro del lado servidor, p. ej. `id=eq.<uuid>`. Reduce el tráfico inútil. */
  filter?: string
}

/**
 * Se suscribe a las tablas indicadas y llama a `onChange` en cada INSERT,
 * UPDATE o DELETE.
 *
 * `tables` se pasa por valor y cambia de identidad en cada render, así que la
 * suscripción se ancla a su forma serializada: sin eso, el efecto se
 * desuscribiría y volvería a suscribirse en bucle en cada render.
 */
export function useRealtime(
  tables: RealtimeTable[],
  onChange: () => void,
): RealtimeStatus {
  const [status, setStatus] = useState<RealtimeStatus>('connecting')

  // El callback se guarda en una ref para que cambiar de handler no obligue a
  // rehacer la suscripción (el websocket se mantiene abierto).
  const handler = useRef(onChange)
  handler.current = onChange

  const key = JSON.stringify(tables)

  useEffect(() => {
    const subscriptions: RealtimeTable[] = JSON.parse(key)

    // Nombre único por conjunto de tablas: dos componentes distintos no deben
    // compartir canal, porque al desmontarse uno cerraría el del otro.
    let channel: RealtimeChannel = supabase.channel(`rt:${key}`)

    for (const { schema, table, filter } of subscriptions) {
      channel = channel.on(
        'postgres_changes',
        { event: '*', schema, table, ...(filter ? { filter } : {}) },
        () => handler.current(),
      )
    }

    channel.subscribe((state) => {
      if (state === 'SUBSCRIBED') setStatus('connected')
      else if (state === 'CHANNEL_ERROR' || state === 'TIMED_OUT') {
        setStatus('error')
      }
    })

    return () => {
      supabase.removeChannel(channel)
    }
  }, [key])

  return status
}

/** Las dos tablas publicadas para Realtime (§8.3). */
export const EMERGENCIES_TABLE: RealtimeTable = {
  schema: 'intake',
  table: 'emergencies',
}

export const NOTIFICATIONS_TABLE: RealtimeTable = {
  schema: 'notification',
  table: 'notifications',
}
