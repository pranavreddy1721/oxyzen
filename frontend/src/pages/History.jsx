import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import LocationSearch from "@/components/LocationSearch";
import { PageLoader, ErrorState } from "@/components/states";
const RANGES=[{v:"24h",label:"24 Hours"},{v:"7d",label:"7 Days"},{v:"30d",label:"30 Days"}];
export default function History(){
 const {location,setLocation}=useLocation(); const [range,setRange]=useState("7d"); const [points,setPoints]=useState(null); const [error,setError]=useState(false);
 const load=useCallback(async()=>{setError(false);setPoints(null);try{const {data}=await api.get("/aqi/history",{params:{locationId:location.id,lat:location.lat,lon:location.lon,locationName:location.name,locationCountry:location.country,range}});setPoints(data)}catch{setError(true)}},[location,range]);
 useEffect(()=>{load()},[load]);
 return <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8"><div className="mb-6"><h1 className="font-heading text-3xl font-black tracking-tight sm:text-4xl">Historical Analysis</h1><p className="mt-1 text-muted-foreground">Historical charts are shown only when the selected live provider supplies historical data.</p></div><div className="mb-6 max-w-3xl"><LocationSearch onSelect={setLocation}/></div><div className="mb-6 flex gap-2">{RANGES.map(r=><button key={r.v} onClick={()=>setRange(r.v)} className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${range===r.v?"border-primary bg-primary/10 text-primary":"border-border text-muted-foreground"}`}>{r.label}</button>)}</div>{error?<ErrorState onRetry={load}/>:!points?<PageLoader/>:<div className="rounded-xl border border-border bg-card p-8"><h2 className="font-heading text-xl font-bold">Historical data unavailable</h2><p className="mt-2 max-w-2xl text-sm text-muted-foreground">The live WAQI API used by OxyZen does not provide general historical series through this endpoint. OxyZen will not generate or fabricate historical values.</p><p className="mt-4 text-xs text-muted-foreground">Requested range: {range}. Location: {location.name}.</p></div>}</div>;
}
