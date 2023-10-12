package com.example.app.pojo;


public class ClaudeResponse {
    
    private String completion;
    private String stop_reason;

    public String getCompletion() {
        return completion;
    }
    public void setCompletion(String completion) {
        this.completion = completion;
    }
    public String getStop_reason() {
        return stop_reason;
    }
    public void setStop_reason(String stop_reason) {
        this.stop_reason = stop_reason;
    }

}
