import type { NextConfig } from "next";

const config: NextConfig = {
  output: "export", // static HTML in out/, deployable anywhere
  trailingSlash: true,
  images: { unoptimized: true },
};

export default config;
