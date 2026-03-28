// 8-bit Booth radix-2 multiplier (unsigned-only subset).
//
// Algorithm: each step, examine {Q[0], Q_neg1}:
//   2'b01 → A_booth = A + M   (add multiplicand)
//   2'b10 → A_booth = A - M   (subtract multiplicand)
//   2'b00, 2'b11 → A_booth = A (no-op)
// Then arithmetic-right-shift {A, Q, Q_neg1} using A_booth:
//   {A, Q, Q_neg1} <= {A_booth[7], A_booth, Q}
// After 8 steps, product = {A, Q}.
//
// Protocol: assert start for one cycle. After 10 cycles, done pulses
// with valid product. Assumes inputs are small positive (MSB=0).
//
// Three bugs corrupt the Booth encoding, shift, and product assembly.
module booth_mul(
  input  clk,
  input  reset,
  input  start,
  input  [7:0] multiplicand,
  input  [7:0] multiplier_in,
  output reg [15:0] product,
  output reg        done
);
  reg [7:0] A;          // accumulator (upper half)
  reg [7:0] Q;          // multiplier shift register (lower half)
  reg       Q_neg1;     // previous Q[0]
  reg [7:0] M;          // latched multiplicand
  reg [7:0] saved_mplr; // latched multiplier (for properties)
  reg [3:0] step;       // 0..7 = iteration, 8 = commit
  reg       running;

  // Combinational: Booth add/subtract step
  wire [7:0] A_booth = ({Q[0], Q_neg1} == 2'b01) ? (A + M) :
                        ({Q[0], Q_neg1} == 2'b10) ? (A - M) :
                        A;

  initial begin
    A = 0; Q = 0; Q_neg1 = 0; M = 0; saved_mplr = 0;
    step = 0; running = 0; product = 0; done = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      A <= 0; Q <= 0; Q_neg1 <= 0; M <= 0; saved_mplr <= 0;
      step <= 0; running <= 0; product <= 0; done <= 0;
    end else if (start && !running) begin
      A <= 0; Q <= multiplier_in; Q_neg1 <= 0;
      M <= multiplicand; saved_mplr <= multiplier_in;
      step <= 0; running <= 1; done <= 0;
    end else if (running) begin
      if (step == 4'd7) begin
        product  <= {A[6:0], 1'b0, Q};
        done     <= 1;
        running  <= 0;
        step     <= 0;
      end else begin
        // Shift with Booth result
        {A, Q, Q_neg1} <= {A_booth[7], A_booth, Q[7:1], Q[1]};
        step <= step + 1;
      end
    end else begin
      done <= 0;
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> !done);
  p_done_pulse: assert property (@(posedge clk) done |=> !done || reset);
  p_test_3x4:   assert property (@(posedge clk) done && M == 8'd3 && saved_mplr == 8'd4 |-> product == 16'd12);
  p_test_5x7:   assert property (@(posedge clk) done && M == 8'd5 && saved_mplr == 8'd7 |-> product == 16'd35);
  p_test_1x100: assert property (@(posedge clk) done && M == 8'd1 && saved_mplr == 8'd100 |-> product == 16'd100);
  p_identity:   assert property (@(posedge clk) done |-> product[7:0] == Q && product[15:8] == A);
endmodule
