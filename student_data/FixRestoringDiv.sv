// 8-bit restoring division: computes quotient = dividend / divisor,
// remainder = dividend % divisor using the restoring algorithm.
//
// Protocol: assert start=1 for one cycle. After 10 cycles, done pulses
// for one cycle with valid quotient and remainder. Assumes divisor != 0.
//
// Restoring algorithm (one step per clock):
//   step 0..7: bring in dividend[7-step] (MSB first) into partial_remainder,
//              subtract divisor; if result negative, restore and set quotient bit=0,
//              else keep and set quotient bit=1.
//   step 8:    commit quotient and remainder; assert done.
//
module restoring_div(
  input  clk,
  input  reset,
  input  start,
  input  [7:0] dividend,
  input  [7:0] divisor,
  output reg [7:0] quotient,
  output reg [7:0] remainder,
  output reg       done
);
  reg [7:0] n_reg;    // latched dividend
  reg [7:0] d_reg;    // latched divisor
  reg [7:0] pr;       // partial remainder
  reg [7:0] q_acc;    // quotient accumulator
  reg [3:0] step;     // 0..7 = iteration, 8 = commit
  reg       running;

  // Initial values needed for EBMC (checks properties from time 0)
  initial begin
    done = 0; running = 0; step = 0; pr = 0; q_acc = 0;
    quotient = 0; remainder = 0; n_reg = 0; d_reg = 0;
  end

  // Combinational: shifted partial_remainder for this iteration
  // Bring in next dividend bit MSB-first: n_reg[7], n_reg[6], ..., n_reg[0]
  wire [7:0] pr_sh = {n_reg[7-step], pr[7:1]};
  wire [8:0] pr_sub = {1'b0, pr_sh} - {1'b0, d_reg};

  always @(posedge clk) begin
    if (reset) begin
      done <= 0; running <= 0; step <= 0;
      pr <= 0; q_acc <= 0; quotient <= 0; remainder <= 0;
      n_reg <= 0; d_reg <= 0;
    end else if (start && !running) begin
      done    <= 0;
      running <= 1;
      step    <= 4'd1;
      pr      <= 0;
      q_acc   <= 0;
      n_reg   <= dividend;
      d_reg   <= divisor;
    end else if (running) begin
      if (step == 4'd7) begin
        // Commit cycle: latch final result
        quotient  <= q_acc;
        remainder <= pr;
        done      <= 1;
        running   <= 0;
        step      <= 0;
      end else begin
        // One restoring-division iteration
        if (pr_sub[8] == 1'b0) begin   // non-negative: keep subtraction
          pr    <= pr_sub[7:0];
          q_acc <= {q_acc[6:0], 1'b1};
        end else begin                  // negative: restore
          pr    <= pr_sh;
          q_acc <= {q_acc[6:0], 1'b0};
        end
        step <= step + 1;
      end
    end else begin
      done <= 0;
    end
  end

  p_done_clr:   assert property (@(posedge clk) reset |=> !done);
  p_identity:   assert property (@(posedge clk) done && d_reg != 8'd0 |-> (quotient * d_reg + remainder == n_reg));
  p_rem_bound:  assert property (@(posedge clk) done && d_reg != 8'd0 |-> (remainder < d_reg));
  p_test_17_5:  assert property (@(posedge clk) done && n_reg == 8'd17  && d_reg == 8'd5 |-> quotient == 8'd3  && remainder == 8'd2);
  p_test_100_7: assert property (@(posedge clk) done && n_reg == 8'd100 && d_reg == 8'd7 |-> quotient == 8'd14 && remainder == 8'd2);
endmodule
