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

// src/services/s3-event-processor.ts
var s3_event_processor_exports = {};
__export(s3_event_processor_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(s3_event_processor_exports);
var handler = async (event) => {
  console.log("Event: ", event);
  const fileName = event.detail.object.key;
  const eventType = event["detail-type"];
  const typeOfS3Event = {
    fileName,
    eventType
  };
  console.log("S3 Event Processor Lambda Output: ", typeOfS3Event);
  return typeOfS3Event;
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
