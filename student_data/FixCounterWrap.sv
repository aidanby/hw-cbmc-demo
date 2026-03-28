// BCD counter: counts 0-9 and wraps back to 0.
// The counter is not wrapping correctly at the end of its range.
module bcd_counter(input clk, input reset, output reg [3:0] count);
  initial count = 0;
  always @(posedge clk) begin
    if (reset)
      count <= 0;
    else if (count >= 4'd10)
      count <= 4'd1;
    else
      count <= count + 1;
  end

  p_range:    assert property (@(posedge clk) count <= 9);
  p_wrap:     assert property (@(posedge clk) count == 9 |=> count == 0);
  p_inc:      assert property (@(posedge clk) !reset && count < 9 |=> count == $past(count) + 1);
  p_wrap_val: assert property (@(posedge clk) !reset && count >= 9 |=> count == 0);
endmodule
