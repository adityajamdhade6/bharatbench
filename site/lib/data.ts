import raw from "../data/leaderboard.json";
import type { Leaderboard } from "./types";

// Every number on the site comes from this one file (written by `bharatbench export`).
export const data = raw as unknown as Leaderboard;
