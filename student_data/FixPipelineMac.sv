// 3-stage pipelined Multiply-Accumulate (MAC) unit.
//
// Stage 1: latch inputs a_in, b_in, clear_acc into a_s1, b_s1, clr_s1
// Stage 2: compute product = a_s1 * b_s1, pipeline clear -> clr_s2
// Stage 3: if clr_s2, acc = 0; else acc += product
//
// Result appears 3 cycles after inputs are presented.
// Due to NBA semantics, each stage reads OLD register values.
//
// Three bugs corrupt the product, clear timing, and accumulation.
module pipe_mac(
  input  clk,
  input  reset,
  input  [7:0] a_in, b_in,
  input  clear_acc,
  output reg [15:0] acc
);
  reg [7:0]  a_s1, b_s1;
  reg        clr_s1, clr_s2;
  reg [15:0] prod_s2;

  initial begin
    a_s1 = 0; b_s1 = 0; clr_s1 = 0; clr_s2 = 0;
    prod_s2 = 0; acc = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      a_s1 <= 0; b_s1 <= 0; clr_s1 <= 0; clr_s2 <= 0;
      prod_s2 <= 0; acc <= 0;
    end else begin
      // Stage 1: latch inputs
      a_s1   <= a_in;
      b_s1   <= b_in;
      clr_s1 <= clear_acc;

      // Stage 2: compute product, pipeline clear
      prod_s2 <= b_s1 * b_s1;
      clr_s2  <= clear_acc;

      // Stage 3: accumulate or clear
      if (clr_s1) begin
        acc <= 16'd0;
      end else begin
        acc <= prod_s2;
      end
    end
  end

  p_reset:     assert property (@(posedge clk) reset |=> acc == 16'd0);
  p_prod:      assert property (@(posedge clk) !reset |=> prod_s2 == ($past(a_s1) * $past(b_s1)));
  p_accum:     assert property (@(posedge clk) !reset && !clr_s2 |=> acc == ($past(acc) + $past(prod_s2)));
  p_clear_eff: assert property (@(posedge clk) !reset && clr_s2 |=> acc == 16'd0);
  p_mul_3x5:   assert property (@(posedge clk) !reset && a_s1 == 8'd3 && b_s1 == 8'd5 |=> reset || prod_s2 == 16'd15);
  p_mul_7x2:   assert property (@(posedge clk) !reset && a_s1 == 8'd7 && b_s1 == 8'd2 |=> reset || prod_s2 == 16'd14);
endmodule
