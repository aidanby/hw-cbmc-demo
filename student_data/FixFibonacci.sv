// Fibonacci generator: outputs successive Fibonacci numbers each clock cycle.
// Sequence after reset: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...
// The module is not generating the correct Fibonacci sequence.
module fibonacci(input clk, input reset, output reg [7:0] curr);
  reg [7:0] prev;

  initial begin
    curr = 0;
    prev = 1;
  end

  always @(posedge clk) begin
    if (reset) begin
      curr <= 1;
      prev <= 0;
    end else begin
      prev <= curr;
      curr <= prev;
    end
  end

  p_init_curr:  assert property (@(posedge clk) reset |=> curr == 0);
  p_init_prev:  assert property (@(posedge clk) reset |=> prev == 1);
  p_step:       assert property (@(posedge clk) !reset |=> curr == $past(prev) + $past(curr));
  p_no_shrink:  assert property (@(posedge clk) !reset && curr < 20 |=> curr >= $past(curr));
endmodule
