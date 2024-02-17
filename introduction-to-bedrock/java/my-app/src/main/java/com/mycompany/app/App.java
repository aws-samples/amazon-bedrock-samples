package com.mycompany.app;

import java.net.HttpURLConnection;
import java.net.URL;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider;

public class App {

    public static void main(String[] args) throws IOException {
        
        ProfileCredentialsProvider credentialsProvider = ProfileCredentialsProvider.create();
        
        String awsIdentity = credentialsProvider.resolveCredentials().accessKeyId();
        String awsSecret = credentialsProvider.resolveCredentials().secretAccessKey();
        String awsRegion = "us-east-1";
        String awsService = "bedrock";
        String model = "meta.llama2-13b-chat-v1";

        System.out.println("************************************************");
        System.out.println("*        Executing sample 'invokeModel'        *");
        System.out.println("************************************************");

        try {
            URL url = new URL("https://bedrock-runtime." + awsRegion + ".amazonaws.com/model/" + model + "/invoke");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            System.out.println(connection.getRequestMethod() + " " + url);
            
            String payload = "{\n"
                + "    \"prompt\": \"[INST]what is your name[INST]\",\n"
                + "    \"temperature\": 0.5,\n"
                + "    \"top_p\": 0.9,\n"
                + "    \"max_gen_len\": 512\n"
                + "  }";

            byte[] bodyBytes = payload.getBytes(StandardCharsets.UTF_8);

            Map<String, String> headers = new LinkedHashMap<>();
            String isoDate = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'")
                    .format(ZonedDateTime.now(ZoneOffset.UTC));
                    
            calculateAuthorizationHeaders(
                    connection.getRequestMethod(),
                    connection.getURL().getHost(),
                    connection.getURL().getPath(),
                    connection.getURL().getQuery(),
                    headers,
                    bodyBytes,
                    isoDate,
                    awsIdentity,
                    awsSecret,
                    awsRegion,
                    awsService);

            // Unsigned headers
            headers.put("Content-Type", "application/json"); 
            headers.put("content-length", "" + payload.length());
            headers.put("accept", "application/json");

            // Log headers and body
            System.out.println(headers.entrySet().stream().map(e -> e.getKey() + ": " + e.getValue())
                    .collect(Collectors.joining("\n")));
            System.out.println(payload);

            // Send
            headers.forEach((key, val) -> connection.setRequestProperty(key, val));
            connection.setDoOutput(true);
            connection.getOutputStream().write(bodyBytes);
            connection.getOutputStream().flush();

            int responseCode = connection.getResponseCode();
            System.out.println("connection.getResponseCode()=" + responseCode);

            String responseContentType = connection.getHeaderField("Content-Type");
            System.out.println("responseContentType=" + responseContentType);

            System.out.println("Response BODY:");
            if (connection.getErrorStream() != null) {
                System.out.println(new String(connection.getErrorStream().readAllBytes(), StandardCharsets.UTF_8));
            } else {
                System.out.println(new String(connection.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

    }
    
    private static void calculateAuthorizationHeaders(
            String method, String host, String path, String query, Map<String, String> headers,
            byte[] body,
            String isoDateTime,
            String awsIdentity, String awsSecret, String awsRegion, String awsService
    ) {
        try {
            String bodySha256 = hex(sha256(body));
            String isoJustDate = isoDateTime.substring(0, 8); // Cut the date portion of a string like '20150830T123600Z';

            headers.put("Host", host);
            headers.put("X-Amz-Content-Sha256", bodySha256);
            headers.put("X-Amz-Date", isoDateTime);

            // (1) https://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
            List<String> canonicalRequestLines = new ArrayList<>();
            canonicalRequestLines.add(method);
            canonicalRequestLines.add(path);
            canonicalRequestLines.add(query);
            List<String> hashedHeaders = new ArrayList<>();
            List<String> headerKeysSorted = headers.keySet().stream().sorted(Comparator.comparing(e -> e.toLowerCase(Locale.US))).collect(Collectors.toList());
            for (String key : headerKeysSorted) {
                hashedHeaders.add(key.toLowerCase(Locale.US));
                canonicalRequestLines.add(key.toLowerCase(Locale.US) + ":" + normalizeSpaces(headers.get(key)));
            }
            canonicalRequestLines.add(null); // new line required after headers
            String signedHeaders = hashedHeaders.stream().collect(Collectors.joining(";"));
            canonicalRequestLines.add(signedHeaders);
            canonicalRequestLines.add(bodySha256);
            String canonicalRequestBody = canonicalRequestLines.stream().map(line -> line == null ? "" : line).collect(Collectors.joining("\n"));
            String canonicalRequestHash = hex(sha256(canonicalRequestBody.getBytes(StandardCharsets.UTF_8)));

            // (2) https://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html
            List<String> stringToSignLines = new ArrayList<>();
            stringToSignLines.add("AWS4-HMAC-SHA256");
            stringToSignLines.add(isoDateTime);
            String credentialScope = isoJustDate + "/" + awsRegion + "/" + awsService + "/aws4_request";
            stringToSignLines.add(credentialScope);
            stringToSignLines.add(canonicalRequestHash);
            String stringToSign = stringToSignLines.stream().collect(Collectors.joining("\n"));

            // (3) https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
            byte[] kDate = hmac(("AWS4" + awsSecret).getBytes(StandardCharsets.UTF_8), isoJustDate);
            byte[] kRegion = hmac(kDate, awsRegion);
            byte[] kService = hmac(kRegion, awsService);
            byte[] kSigning = hmac(kService, "aws4_request");
            String signature = hex(hmac(kSigning, stringToSign));

            String authParameter = "AWS4-HMAC-SHA256 Credential=" + awsIdentity + "/" + credentialScope + ", SignedHeaders=" + signedHeaders + ", Signature=" + signature;
            headers.put("Authorization", authParameter);

        } catch (Exception e) {
            if (e instanceof RuntimeException) {
                throw (RuntimeException) e;
            } else {
                throw new IllegalStateException(e);
            }
        }
    }

    private static String normalizeSpaces(String value) {
        return value.replaceAll("\\s+", " ").trim();
    }

    public static String hex(byte[] a) {
        StringBuilder sb = new StringBuilder(a.length * 2);
        for(byte b: a) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
     }

    private static byte[] sha256(byte[] bytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        digest.update(bytes);
        return digest.digest();
    }

    public static byte[] hmac(byte[] key, String msg) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        return mac.doFinal(msg.getBytes(StandardCharsets.UTF_8));
    }
}