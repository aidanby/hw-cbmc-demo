// Dual-compare timer with prescaler, auto-reload, and interrupt masking.
//
// A 4-bit prescaler divides the clock by 16 (wraps 0..15). On each prescaler
// overflow (15→0) a 'tick' signal pulses, incrementing the 8-bit timer.
//
// Two compare channels (A and B) independently match against the timer:
//   - When timer reaches cmp_a, irq_a fires (if not masked by mask_a).
//   - When timer reaches cmp_b, irq_b fires (if not masked by mask_b).
//
// Auto-reload: when timer reaches cmp_a AND reload is set, timer resets to 0.
// This creates a periodic timer with period = cmp_a.
//
// The prescaler overflow, timer increment, compare match, reload, and masking
// all interact through the timer value feedback path.
module timer_irq(
  input        clk,
  input        reset,
  input  [7:0] cmp_a,
  input  [7:0] cmp_b,
  input        mask_a,       // 1 = mask (suppress) irq_a
  input        mask_b,
  input        reload,       // auto-reload on cmp_a match
  output reg [3:0] prescaler,
  output reg [7:0] timer,
  output reg       tick,
  output reg       irq_a,
  output reg       irq_b
);

  initial begin
    prescaler = 0; timer = 0; tick = 0; irq_a = 0; irq_b = 0;
  end

  // Next timer value after potential increment
  wire [7:0] timer_next = tick ? (timer + 8'd1) : timer;
  // Reload condition
  wire do_reload = reload && (timer_next == cmp_a);

  always @(posedge clk) begin
    if (reset) begin
      prescaler <= 0; timer <= 0; tick <= 0; irq_a <= 0; irq_b <= 0;
    end else begin
      // Prescaler
      if (prescaler == 4'd15) begin
        prescaler <= 4'd0;
        tick      <= 1'b1;
      end else begin
        prescaler <= prescaler + 4'd1;
        tick      <= 1'b0;
      end

      // Timer update (uses tick from PREVIOUS cycle due to NBA)
      if (tick) begin
        if (do_reload)
          timer <= 8'd0;
        else
          timer <= timer + 8'd1;
      end

      // Compare A
      irq_a <= (timer == cmp_a) && mask_a;      // HINT: check this line carefully

      // Compare B
      irq_b <= (timer_next == prescaler) && !mask_b; // HINT: check this line carefully
    end
  end

  p_reset:     assert property (@(posedge clk) reset |=> !irq_a && !irq_b && timer == 8'd0);
  p_tick_gen:  assert property (@(posedge clk) !reset && prescaler == 4'd15 |=> tick);
  p_timer_inc: assert property (@(posedge clk) !reset && tick && !do_reload |=> timer == ($past(timer) + 8'd1));
  p_reload:    assert property (@(posedge clk) !reset && tick && do_reload |=> timer == 8'd0);
  p_irq_a:     assert property (@(posedge clk) !reset && timer_next == cmp_a && !mask_a |=> irq_a);
  p_irq_b:     assert property (@(posedge clk) !reset && timer_next == cmp_b && !mask_b |=> irq_b);
  p_mask_a:    assert property (@(posedge clk) !reset && mask_a |=> !irq_a);
endmodule
