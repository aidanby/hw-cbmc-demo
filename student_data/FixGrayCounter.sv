// 4-bit Gray code counter: binary counter whose output is Gray-encoded.
// On reset, gray output should be 0. Each cycle, binary counter increments by 1
// and gray output is computed as: gray = bin ^ (bin >> 1).
// The counter is not producing correct Gray code output.
module gray_counter(input clk, input reset, output reg [3:0] gray);
  reg [3:0] bin;
  initial begin bin = 0; gray = 0; end

  always @(posedge clk) begin
    if (reset) begin
      bin  <= 0;
      gray <= 4'hF;        // should be 4'h0
    end else begin
      bin  <= bin + 4'd2;  // should be + 4'd1
      gray <= bin ^ (bin >> 2);  // should be >> 1
    end
  end

  p_reset: assert property (@(posedge clk) reset |=> gray == 4'h0);
  p_step:  assert property (@(posedge clk) !reset |=> bin == ($past(bin) + 4'd1));
  p_formula: assert property (@(posedge clk) !reset |=> gray == ($past(bin) ^ ($past(bin) >> 1)));
endmodule
