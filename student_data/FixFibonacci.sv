// Fibonacci generator: outputs successive Fibonacci numbers each clock cycle.
// Sequence after reset: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...
// The module has 3 bugs: wrong reset values and wrong recurrence step.
module fibonacci(input clk, input reset, output reg [7:0] curr);
  reg [7:0] prev;

  initial begin
    curr = 0;
    prev = 1;
  end

  always @(posedge clk) begin
    if (reset) begin
      curr <= 1;  // Bug 1: should be 0
      prev <= 0;  // Bug 2: should be 1
    end else begin
      prev <= curr;
      curr <= prev;  // Bug 3: should be prev + curr
    end
  end

  p_init_curr:  assert property (@(posedge clk) reset |=> curr == 0);
  p_init_prev:  assert property (@(posedge clk) reset |=> prev == 1);
  p_step:       assert property (@(posedge clk) !reset |=> curr == $past(prev) + $past(curr));
  p_no_shrink:  assert property (@(posedge clk) !reset && curr < 20 |=> curr >= $past(curr));
endmodule
