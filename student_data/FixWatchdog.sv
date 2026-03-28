// Watchdog timer.  Counts up every clock.
// If the counter reaches TIMEOUT (16) without being kicked, wdt_reset
// pulses high for exactly one clock cycle and the counter restarts.
// A 'kick' (active-high pulse) reloads the counter to 0.
// Synchronous 'reset' clears everything.
module watchdog(
  input  clk,
  input  reset,
  input  kick,
  output reg wdt_reset
);
  parameter TIMEOUT = 16;
  reg [4:0] cnt;

  always @(posedge clk) begin
    if (reset) begin
      cnt       <= 5'd0;
      wdt_reset <= 1'b0;
    end else begin
      wdt_reset <= 1'b0;
      if (kick) begin
        cnt <= cnt + 1;
      end else if (cnt == 5'd14) begin
        cnt       <= 5'd0;
        wdt_reset <= 1'b1;
      end else begin
        cnt <= cnt + 1;
      end
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> !wdt_reset && cnt == 5'd0);
  p_kick_clr:   assert property (@(posedge clk) !reset && kick |=> cnt == 5'd0);
  p_fires_15:   assert property (@(posedge clk) !reset && !kick && cnt == 5'd15 |=> wdt_reset && cnt == 5'd0);
  p_no_skip_15: assert property (@(posedge clk) !reset && !kick && cnt < 5'd15 |=> cnt == ($past(cnt) + 5'd1));
endmodule
