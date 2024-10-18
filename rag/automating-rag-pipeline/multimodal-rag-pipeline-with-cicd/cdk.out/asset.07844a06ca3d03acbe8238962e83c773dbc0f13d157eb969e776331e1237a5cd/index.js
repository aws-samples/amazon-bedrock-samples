"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/services/evaluate-new-data-ingestion.ts
var evaluate_new_data_ingestion_exports = {};
__export(evaluate_new_data_ingestion_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(evaluate_new_data_ingestion_exports);
var handler = async (event) => {
  console.log("Evaluate New Data Ingestion Lambda!");
  const ingestionResult = { "successRate": 85 };
  if (!ingestionResult || typeof ingestionResult.successRate === "undefined") {
    console.log("Ingestion result or successRate is missing.");
    return {
      success: false,
      message: "Missing ingestion result or successRate in event payload."
    };
  }
  console.log("Ingestion Result:", JSON.stringify(ingestionResult, null, 2));
  const threshold = 80;
  if (ingestionResult.successRate >= threshold) {
    console.log("Ingestion success rate meets the threshold. Evaluation passed.");
    return {
      success: true,
      message: "Proceed to production"
    };
  } else {
    console.log("Ingestion success rate below threshold. Evaluation failed.");
    return {
      success: false,
      message: "Evaluation failed. Do not proceed to production"
    };
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
